import re
import httpx
import asyncio
import aiofiles
import subprocess

from nonebot import on_keyword, on_message
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, MessageEvent, Bot, MessageSegment

from bilibili_api import video, live, article, Credential
from bilibili_api.favorite_list import get_video_favorite_list_content
from bilibili_api.opus import Opus
from bilibili_api.video import VideoDownloadURLDataDetecter
from urllib.parse import parse_qs, urlparse

from .utils import *
from .filter import is_not_in_disable_group
from ..data_source.common import delete_boring_characters

from ..config import *
from ..cookie import cookies_str_to_dict

# format cookie
credential: Credential = Credential.from_cookies(cookies_str_to_dict(rconfig.r_bili_ck)) if rconfig.r_bili_ck else None

# 哔哩哔哩的头请求
BILIBILI_HEADER = {
    'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 '
        'Safari/537.36',
    'referer': 'https://www.bilibili.com',
}

async def is_bilibili(event: MessageEvent) -> bool:
    message = str(event.message).strip()
    return any(key in message for key in {"bilibili.com", "b23.tv", "BV"})

bilibili = on_message(rule = Rule(is_bilibili, is_not_in_disable_group))

@bilibili.handle()
async def _(bot: Bot, event: MessageEvent) -> None:

    # 合并转发消息 list
    segs: List[MessageSegment | str] = []
    will_delete_id = 0

    # 消息
    url: str = str(event.message).strip()

    # 正则匹配
    url_reg = r"(http:|https:)\/\/(space|www|live).bilibili.com\/[A-Za-z\d._?%&+\-=\/#]*"
    b_short_reg = r"(http:|https:)\/\/b23.tv\/[A-Za-z\d._?%&+\-=\/#]*"
    # BV处理
    if re.match(r'^BV[1-9a-zA-Z]{10}$', url):
        url = 'https://www.bilibili.com/video/' + url
    # 处理短号、小程序问题
    if 'b23.tv' in url or ('b23.tv' and 'QQ小程序' in url):
        b_short_url = re.search(b_short_reg, url.replace("\\", ""))[0]
        async with httpx.AsyncClient as client:
            resp = await client.get(b_short_url, headers=BILIBILI_HEADER, follow_redirects=True)
        url: str = str(resp.url)
    else:
        if match := re.search(url_reg, url):
            url = match.group(0)
    # ===============发现解析的是动态，转移一下===============
    if ('t.bilibili.com' in url or '/opus' in url) and credential:
        # 去除多余的参数
        if '?' in url:
            url = url[:url.index('?')]
        dynamic_id = int(re.search(r'[^/]+(?!.*/)', url)[0])
        dynamic_info = await Opus(dynamic_id, credential).get_info()
        # 这里比较复杂，暂时不用管，使用下面这个算法即可实现哔哩哔哩动态转发
        if dynamic_info is not None:
            title = dynamic_info['item']['basic']['title']
            paragraphs = []
            for module in dynamic_info['item']['modules']:
                if 'module_content' in module:
                    paragraphs = module['module_content']['paragraphs']
                    break
            desc = paragraphs[0]['text']['nodes'][0]['word']['words']
            pics = paragraphs[1]['pic']['pics']
            await bilibili.send(Message(f"{NICKNAME}解析 | B站动态 - {title}\n{desc}"))
            send_pics = []
            for pic in pics:
                img = pic['url']
                send_pics.append(make_node_segment(bot.self_id, MessageSegment.image(img)))
            # 发送异步后的数据
            await send_forward_both(bot, event, send_pics)
        return
    # 直播间解析
    if 'live' in url:
        # https://live.bilibili.com/30528999?hotRank=0
        room_id = re.search(r'\/(\d+)', url).group(1)
        room = live.LiveRoom(room_display_id=int(room_id))
        room_info = (await room.get_room_info())['room_info']
        title, cover, keyframe = room_info['title'], room_info['cover'], room_info['keyframe']
        await bilibili.send(Message([MessageSegment.image(cover), MessageSegment.image(keyframe),
                                   MessageSegment.text(f"{NICKNAME}解析 | 哔哩哔哩直播 - {title}")]))
        return
    # 专栏解析
    if 'read' in url:
        read_id = re.search(r'read\/cv(\d+)', url).group(1)
        ar = article.Article(read_id)
        # 如果专栏为公开笔记，则转换为笔记类
        # NOTE: 笔记类的函数与专栏类的函数基本一致
        if ar.is_note():
            ar = ar.turn_to_note()
        # 加载内容
        await ar.fetch_content()
        markdown_path = plugin_cache_dir / 'article.md'
        with open(markdown_path, 'w', encoding='utf8') as f:
            f.write(ar.markdown())
        await bilibili.send(Message(f"{NICKNAME}解析 | 哔哩哔哩专栏"))
        await bilibili.finish(Message(MessageSegment(type="file", data={ "file": markdown_path })))
    # 收藏夹解析
    if 'favlist' in url and credential:
        # https://space.bilibili.com/22990202/favlist?fid=2344812202
        fav_id = re.search(r'favlist\?fid=(\d+)', url).group(1)
        fav_list = (await get_video_favorite_list_content(fav_id))['medias'][:10]
        favs = []
        for fav in fav_list:
            title, cover, intro, link = fav['title'], fav['cover'], fav['intro'], fav['link']
            logger.info(title, cover, intro)
            favs.append(
                [MessageSegment.image(cover),
                 MessageSegment.text(f'🧉 标题：{title}\n📝 简介：{intro}\n🔗 链接：{link}')])
        await bilibili.send(f'{NICKNAME}解析 | 哔哩哔哩收藏夹，正在为你找出相关链接请稍等...')
        await bilibili.finish(make_node_segment(bot.self_id, favs))
    # 获取视频信息
    will_delete_id: int = (await bilibili.send(f'{NICKNAME}解析 | 哔哩哔哩, 解析中.....'))["message_id"]
    video_id = re.search(r"video\/[^\?\/ ]+", url)[0].split('/')[1]
    if "av" in video_id:
        v = video.Video(aid=int(video_id.split("av")[1]), credential=credential)
    else:
        v = video.Video(bvid=video_id, credential=credential)
    try:
        video_info = await v.get_info()
    except Exception as e:
        await bilibili.finish(Message(f"{NICKNAME}解析 | 哔哩哔哩，出错，{e}"))
    if video_info is None:
        await bilibili.finish(Message(f"{NICKNAME}解析 | 哔哩哔哩，出错，无法获取数据！"))
    video_title, video_cover, video_desc, video_duration = video_info['title'], video_info['pic'], video_info['desc'], \
        video_info['duration']
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
    video_title = delete_boring_characters(video_title)
    # 截断下载时间比较长的视频
    online = await v.get_online()
    online_str = f'🏄‍♂️ 总共 {online["total"]} 人在观看，{online["count"]} 人在网页端观看'
    segs.append(MessageSegment.image(video_cover))
    segs.append(f"{video_title}\n{extra_bili_info(video_info)}\n📝 简介：{video_desc}\n{online_str}")
    if video_duration > DURATION_MAXIMUM:
        segs.append(f"⚠️ 当前视频时长 {video_duration // 60} 分钟，超过管理员设置的最长时间 {DURATION_MAXIMUM // 60} 分钟!")
    else:
        # 下载视频和音频
        try:
            download_url_data = await v.get_download_url(page_index=page_num)
            detecter = VideoDownloadURLDataDetecter(download_url_data)
            streams = detecter.detect_best_streams()
            video_url, audio_url = streams[0].url, streams[1].url
            # 下载视频和音频
            await asyncio.gather(
                    download_b_file(video_url, f"{video_id}-video.m4s", logger.debug),
                    download_b_file(audio_url, f"{video_id}-audio.m4s", logger.debug))
            await merge_file_to_mp4(f"{video_id}-video.m4s", f"{video_id}-audio.m4s", f"{video_id}-res.mp4")
            segs.append(await get_video_seg(file_name=f"{video_id}-res.mp4"))
        except Exception as e:
            logger.error(f"下载视频失败，\n{e}")
            segs.append(f"下载视频失败，\n{e}")
     # 这里是总结内容，如果写了 cookie 就可以
    if credential:
        ai_conclusion = await v.get_ai_conclusion(await v.get_cid(0))
        if ai_conclusion['model_result']['summary'] != '':
            segs.append(f"bilibili AI总结:\n{ai_conclusion['model_result']['summary']}")
    await send_forward_both(bot, event, make_node_segment(bot.self_id, segs))
    await bot.delete_msg(message_id = will_delete_id)



async def download_b_file(url, file_name, progress_callback):
    """
        下载视频文件和音频文件
    :param url:
    :param full_file_name:
    :param progress_callback:
    :return:
    """
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, headers=BILIBILI_HEADER) as resp:
            current_len = 0
            total_len = int(resp.headers.get('content-length', 0))
            async with aiofiles.open(plugin_cache_dir / file_name, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    current_len += len(chunk)
                    await f.write(chunk)
                    progress_callback(f'下载进度：{round(current_len / total_len, 3)}')

async def merge_file_to_mp4(v_name: str, a_name: str, output_file_name: str, log_output: bool = False):
    """
    合并视频文件和音频文件
    :param v_full_file_name: 视频文件路径
    :param a_full_file_name: 音频文件路径
    :param output_file_name: 输出文件路径
    :param log_output: 是否显示 ffmpeg 输出日志，默认忽略
    :return:
    """
    logger.info(f'正在合并：{output_file_name}')

    # 构建 ffmpeg 命令
    command = f'ffmpeg -y -i "{plugin_cache_dir / v_name}" -i "{plugin_cache_dir / a_name}" -c copy "{plugin_cache_dir / output_file_name}"'
    stdout = None if log_output else subprocess.DEVNULL
    stderr = None if log_output else subprocess.DEVNULL
    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.call(command, shell=True, stdout=stdout, stderr=stderr)
    )
    

def extra_bili_info(video_info):
    """
        格式化视频信息
    """
    video_state = video_info['stat']
    video_like, video_coin, video_favorite, video_share, video_view, video_danmaku, video_reply = video_state['like'], \
        video_state['coin'], video_state['favorite'], video_state['share'], video_state['view'], video_state['danmaku'], \
        video_state['reply']

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