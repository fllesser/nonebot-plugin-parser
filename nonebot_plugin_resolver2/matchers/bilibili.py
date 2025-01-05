import re
import httpx
import asyncio

from tqdm.asyncio import tqdm
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.params import CommandArg
from nonebot.exception import ActionFailed
from nonebot.plugin.on import on_message, on_command
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    Bot,
    MessageSegment
)
from bilibili_api import (
    video,
    live,
    article,
    Credential
)
from bilibili_api.favorite_list import get_video_favorite_list_content
from bilibili_api.opus import Opus
from bilibili_api.video import VideoDownloadURLDataDetecter
from urllib.parse import parse_qs, urlparse

from .utils import (
    construct_nodes,
    get_video_seg, 
    get_file_seg
)
from .filter import is_not_in_disable_group
from .preprocess import (
    r_keywords,
    R_KEYWORD_KEY,
    R_EXTRACT_KEY
)
from ..download.common import (
    delete_boring_characters,
    download_file_by_stream,
    download_img,
    merge_av
)

from ..config import (
    rconfig,
    NICKNAME,
    DURATION_MAXIMUM,
    plugin_cache_dir
)
from ..cookie import cookies_str_to_dict

# format cookie
credential: Credential = Credential.from_cookies(cookies_str_to_dict(rconfig.r_bili_ck)) if rconfig.r_bili_ck else None

# 哔哩哔哩的头请求
BILIBILI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87',
    'referer': 'https://www.bilibili.com'
}

bilibili = on_message(
    rule = is_not_in_disable_group & r_keywords("bilibili", "b23", "bili2233", "BV")
)

bili_music = on_command(
    cmd="bm",
    block = True
)

@bilibili.handle()
async def _(bot: Bot, state: T_State):
    # 消息
    text, keyword = state.get(R_EXTRACT_KEY), state.get(R_KEYWORD_KEY)
    url, video_id = '', ''
    
    if keyword == 'BV':
        if re.match(r'^BV[1-9a-zA-Z]{10}$', text):
            video_id = text
    elif keyword in ('b23', 'bili2233'):
        # 处理短号、小程序
        pattern = r"https?://(?:b23\.tv|bili2233\.cn)/[A-Za-z\d\._?%&+\-=/#]+"
        if match := re.search(pattern, text):
            b23url = match.group(0)
            async with httpx.AsyncClient() as client:
                resp = await client.get(b23url, headers=BILIBILI_HEADERS, follow_redirects=True)
            url = str(resp.url)
            if url == b23url:
                logger.info(f"链接 {url} 无效，忽略")
                return
    else:
        pattern = r"https?://(?:space|www|live|m|t)?\.?bilibili\.com/[A-Za-z\d\._?%&+\-=/#]+"
        if match := re.search(pattern, text):
            url = match.group(0)
    if url:
        # 动态
        if 't.bilibili.com' in url or '/opus' in url:
            if match := re.search(r'/(\d+)', url):
                dynamic_id = int(match.group(1))
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到动态 id, 忽略")
                return
            dynamic_info = await Opus(dynamic_id, credential).get_info()
            
            if dynamic_info:
                title = dynamic_info['item']['basic']['title']
                await bilibili.send(f"{NICKNAME}解析 | 哔哩哔哩 - {title}")
                paragraphs = []
                for module in dynamic_info['item']['modules']:
                    if 'module_content' in module:
                        paragraphs = module['module_content']['paragraphs']
                        break
                    
                segs = []
                for node in paragraphs[0]['text']['nodes']:
                    text_type = node.get('type')
                    if text_type == 'TEXT_NODE_TYPE_RICH':
                        segs.append(node['rich']['text'])
                    elif text_type == 'TEXT_NODE_TYPE_WORD':
                        segs.append(node['word']['words'])
                if len(paragraphs) > 1:
                    pics = paragraphs[1]['pic']['pics']
                    segs += [MessageSegment.image(pic['url']) for pic in pics]
                
                await bilibili.finish(construct_nodes(bot.self_id, segs))
        # 直播间解析
        if '/live' in url:
            # https://live.bilibili.com/30528999?hotRank=0
            if match := re.search(r'/(\d+)', url):
                room_id = match.group(1)
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到直播间 id, 忽略")
                return
            room = live.LiveRoom(room_display_id=int(room_id))
            room_info = (await room.get_room_info())['room_info']
            title, cover, keyframe = room_info['title'], room_info['cover'], room_info['keyframe']
            await bilibili.finish(MessageSegment.image(cover) + MessageSegment.image(keyframe) + f"{NICKNAME}解析 | 哔哩哔哩 - 直播 - {title}")
        # 专栏解析
        if '/read' in url:
            if match := re.search(r'read/cv(\d+)', url):
                read_id = match.group(1)
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到专栏 id, 忽略")
                return
            ar = article.Article(read_id)
            await bilibili.send(f"{NICKNAME}解析 | 哔哩哔哩 - 专栏")

            # 加载内容
            await ar.fetch_content()
            data = ar.json()
            segs: list[MessageSegment | str] = []
            def accumulate_text(node):
                text = ""
                if 'children' in node:
                    for child in node['children']:
                        text += accumulate_text(child) + " "
                if _text := node.get('text'):
                    text += _text if isinstance(_text, str) else str(_text) + node.get('url')
                return text
            for node in data.get("children"):
                node_type = node.get('type')
                if node_type == "ImageNode":
                    if img_url := node.get('url'):
                        segs.append(MessageSegment.image(await download_img(img_url)))
                elif node_type == "ParagraphNode":
                    if text := accumulate_text(node).strip():
                        segs.append(text)
                elif node_type == 'TextNode':
                    segs.append(node.get("text"))
            if segs:
                await bilibili.finish(construct_nodes(bot.self_id, segs))
        # 收藏夹解析
        if '/favlist' in url:
            # https://space.bilibili.com/22990202/favlist?fid=2344812202
            if match := re.search(r'favlist\?fid=(\d+)', url):
                fav_id = match.group(1)
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到收藏夹 id, 忽略")
                return
            fav_list = (await get_video_favorite_list_content(fav_id))['medias'][:10]
            favs = []
            for fav in fav_list:
                title, cover, intro, link = fav['title'], fav['cover'], fav['intro'], fav['link']
                avid = re.search(r'\d+', link).group(0)
                favs.append(
                    MessageSegment.image(cover) + 
                    f'🧉 标题：{title}\n📝 简介：{intro}\n🔗 链接：{link}\nhttps://bilibili.com/video/av{avid}'
                )
            await bilibili.send(f'{NICKNAME}解析 | 哔哩哔哩 - 收藏夹\n正在为你找出相关链接请稍等...')
            await bilibili.finish(construct_nodes(bot.self_id, favs))
   
    if video_id:
        v = video.Video(bvid = video_id, credential=credential)
    elif match := re.search(r"(av\d+|BV[A-Za-z0-9]{10})", url):
        video_id = match.group(1)
        if "av" in video_id:
            v = video.Video(aid=int(video_id.split("av")[1]), credential=credential)
        else:
            v = video.Video(bvid=video_id, credential=credential)
    else:
        logger.info(f"链接[{url}]或BV号[{video_id}]无效，忽略")
        return
    # 合并转发消息 list
    segs: list[MessageSegment | str] = []
    try:
        video_info = await v.get_info()
        if not video_info:
            raise Exception("video_info is None")
    except Exception as e:
        await bilibili.finish(f"{NICKNAME}解析 | 哔哩哔哩 - 出错 {e}")
    await bilibili.send(f'{NICKNAME}解析 | 哔哩哔哩 - 视频')
    video_title, video_cover, video_desc, video_duration = video_info['title'], video_info['pic'], video_info['desc'], video_info['duration']
    # 校准 分 p 的情况
    page_num = 0
    if 'pages' in video_info:
        # 解析URL
        parsed_url = urlparse(url)
        # 检查是否有查询字符串
        if parsed_url.query:
            # 解析查询字符串中的参数
            query_params = parse_qs(parsed_url.query)
            # 获取指定参数的值，如果参数不存在，则返回None
            page_num = int(query_params.get('p', [1])[0]) - 1
        else:
            page_num = 0
        if 'duration' in video_info['pages'][page_num]:
            video_duration = video_info['pages'][page_num].get('duration', video_info.get('duration'))
        else:
            # 如果索引超出范围，使用 video_info['duration'] 或者其他默认值
            video_duration = video_info.get('duration', 0)
    # 删除特殊字符
    # video_title = delete_boring_characters(video_title)
    # 截断下载时间比较长的视频
    online = await v.get_online()
    online_str = f'🏄‍♂️ 总共 {online["total"]} 人在观看，{online["count"]} 人在网页端观看'
    segs.append(MessageSegment.image(video_cover))
    segs.append(f"{video_title}\n{extra_bili_info(video_info)}\n📝 简介：{video_desc}\n{online_str}")
    # 这里是总结内容，如果写了 cookie 就可以
    if credential:
        ai_conclusion = await v.get_ai_conclusion(await v.get_cid(0))
        if ai_conclusion['model_result']['summary'] != '':
            segs.append(f"bilibili AI总结:\n{ai_conclusion['model_result']['summary']}")
    if video_duration > DURATION_MAXIMUM:
        segs.append(f"⚠️ 当前视频时长 {video_duration // 60} 分钟，超过管理员设置的最长时间 {DURATION_MAXIMUM // 60} 分钟!")
    await bilibili.send(construct_nodes(bot.self_id, segs))
    if video_duration < DURATION_MAXIMUM:
        # 下载视频和音频
        try:
            video_name = video_id + ".mp4"
            video_path = plugin_cache_dir / video_name
            if not video_path.exists():
                download_url_data = await v.get_download_url(page_index=page_num)
                detecter = VideoDownloadURLDataDetecter(download_url_data)
                streams = detecter.detect_best_streams()
                video_url, audio_url = streams[0].url, streams[1].url
    
                # 下载视频和音频
                v_path, a_path = await asyncio.gather(
                    download_file_by_stream(video_url, f"{video_id}-video.m4s", ext_headers=BILIBILI_HEADERS),
                    download_file_by_stream(audio_url, f"{video_id}-audio.m4s", ext_headers=BILIBILI_HEADERS)
                )
                await merge_av(v_path, a_path, video_path)
            await bilibili.send(await get_video_seg(video_path))
        except Exception as e:
            if not isinstance(e, ActionFailed):
                await bilibili.send(f"下载视频失败 | {e}")

@bili_music.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    bvid = args.extract_plain_text().strip()
    if not re.match(r'^BV[1-9a-zA-Z]{10}$', bvid):
        await bili_music.finish("格式: bm BV...")
    await bot.call_api("set_msg_emoji_like", message_id = event.message_id, emoji_id = '282')
    v = video.Video(bvid = bvid, credential=credential)
    try:
        video_info = await v.get_info()
        #if video_info.get('pages'):
            # todo
            #return
        video_title = delete_boring_characters(video_info.get('title'))
        audio_name = f"{video_title}.mp3"
        audio_path = plugin_cache_dir / audio_name
        if not audio_path.exists():
            download_url_data = await v.get_download_url(page_index=0)
            detecter = VideoDownloadURLDataDetecter(download_url_data)
            streams = detecter.detect_best_streams()
            audio_url = streams[1].url
            await download_file_by_stream(audio_url, audio_name, ext_headers=BILIBILI_HEADERS)
    except Exception as e:
        await bili_music.finish(f'download audio excepted err: {e}')
    await bili_music.send(MessageSegment.record(audio_path))
    await bili_music.send(get_file_seg(audio_path))
    
def extra_bili_info(video_info):
    """
        格式化视频信息
    """
    video_state = video_info['stat']
    video_like, video_coin, video_favorite, video_share, video_view, video_danmaku, video_reply = (
        video_state['like'],
        video_state['coin'],
        video_state['favorite'],
        video_state['share'],
        video_state['view'],
        video_state['danmaku'],
        video_state['reply']
    )

    video_data_map = {
        "点赞": video_like,
        "硬币": video_coin,
        "收藏": video_favorite,
        "分享": video_share,
        "总播放量": video_view,
        "弹幕数量": video_danmaku,
        "评论": video_reply
    }

    video_info_result = ""
    for key, value in video_data_map.items():
        if int(value) > 10000:
            formatted_value = f"{value / 10000:.1f}万"
        else:
            formatted_value = value
        video_info_result += f"{key}: {formatted_value} | "

    return video_info_result