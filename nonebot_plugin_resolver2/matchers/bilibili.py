import re
import httpx
import asyncio

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.params import CommandArg
from nonebot.exception import ActionFailed
from nonebot.plugin.on import on_message, on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from bilibili_api import video, live, article, Credential

from bilibili_api.opus import Opus
from bilibili_api.video import VideoDownloadURLDataDetecter
from bilibili_api.favorite_list import get_video_favorite_list_content

from .utils import construct_nodes, get_video_seg, get_file_seg
from .filter import is_not_in_disable_group
from .preprocess import r_keywords, R_KEYWORD_KEY, R_EXTRACT_KEY
from ..download.common import (
    delete_boring_characters,
    download_file_by_stream,
    download_img,
    merge_av,
)
from ..config import rconfig, NICKNAME, DURATION_MAXIMUM, plugin_cache_dir
from ..cookie import cookies_str_to_dict

# format cookie
credential: Credential = (
    Credential.from_cookies(cookies_str_to_dict(rconfig.r_bili_ck))
    if rconfig.r_bili_ck
    else None
)

# 哔哩哔哩的头请求
BILIBILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87",
    "referer": "https://www.bilibili.com",
}

bilibili = on_message(
    rule=is_not_in_disable_group
    & r_keywords("bilibili", "bili2233", "b23", "BV", "av"),
    priority=5,
)

bili_music = on_command(cmd="bm", block=True)

patterns: dict[str, re.Pattern] = {
    "BV": re.compile(r"(BV[1-9a-zA-Z]{10})(?:\s)?(\d{1,3})?"),
    "av": re.compile(r"av(\d{6,})(?:\s)?(\d{1,3})?"),
    "/BV": re.compile(r"/(BV[1-9a-zA-Z]{10})()"),
    "/av": re.compile(r"/av(\d{6,})()"),
    "b23": re.compile(r"https?://b23\.tv/[A-Za-z\d\._?%&+\-=/#]+()()"),
    "bili2233": re.compile(r"https?://bili2233\.cn/[A-Za-z\d\._?%&+\-=/#]+()()"),
    "bilibili": re.compile(
        r"https?://(?:space|www|live|m|t)?\.?bilibili\.com/[A-Za-z\d\._?%&+\-=/#]+()()"
    ),
}


@bilibili.handle()
async def _(bot: Bot, state: T_State):
    # 消息
    text, keyword = state.get(R_EXTRACT_KEY), state.get(R_KEYWORD_KEY)
    match = patterns[keyword].search(text)
    if not match:
        logger.info(f"{text} 中的链接或id无效, 忽略")
        return
    url, video_id, page_num = match.group(0), match.group(1), match.group(2)

    # 短链重定向地址
    if keyword in ("b23", "bili2233"):
        b23url = url
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                b23url, headers=BILIBILI_HEADERS, follow_redirects=True
            )
        url = str(resp.url)
        if url == b23url:
            logger.info(f"链接 {url} 无效，忽略")
            return

    # 链接中是否包含BV，av号
    if url and (id_type := next((i for i in ("/BV", "/av") if i in url), None)):
        if match := patterns[id_type].search(url):
            keyword = id_type
            video_id = match.group(1)

    # 如果不是视频
    if not video_id:
        # 动态
        if "t.bilibili.com" in url or "/opus" in url:
            if match := re.search(r"/(\d+)", url):
                dynamic_id = int(match.group(1))
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到动态 id, 忽略")
                return
            dynamic_info = await Opus(dynamic_id, credential).get_info()
            if not dynamic_info:
                return
            title = dynamic_info["item"]["basic"]["title"]
            await bilibili.send(f"{NICKNAME}解析 | 哔哩哔哩 - {title}")

            paragraphs = []
            for module in dynamic_info["item"]["modules"]:
                if "module_content" in module:
                    paragraphs = module["module_content"]["paragraphs"]
                    break
            segs = []
            for node in paragraphs[0]["text"]["nodes"]:
                text_type = node.get("type")
                if text_type == "TEXT_NODE_TYPE_RICH":
                    segs.append(node["rich"]["text"])
                elif text_type == "TEXT_NODE_TYPE_WORD":
                    segs.append(node["word"]["words"])
            if len(paragraphs) > 1:
                pics = paragraphs[1]["pic"]["pics"]
                segs += [MessageSegment.image(pic["url"]) for pic in pics]

            await bilibili.finish(construct_nodes(bot.self_id, segs))
        # 直播间解析
        elif "/live" in url:
            # https://live.bilibili.com/30528999?hotRank=0
            if match := re.search(r"/(\d+)", url):
                room_id = match.group(1)
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到直播间 id, 忽略")
                return
            room = live.LiveRoom(room_display_id=int(room_id))
            room_info = (await room.get_room_info())["room_info"]
            title, cover, keyframe = (
                room_info["title"],
                room_info["cover"],
                room_info["keyframe"],
            )
            res = f"{NICKNAME}解析 | 哔哩哔哩 - 直播 内容获取失败"
            if title:
                res = f"{NICKNAME}解析 | 哔哩哔哩 - 直播 - {title}"
                res += MessageSegment.image(cover) if cover else ""
                res += MessageSegment.image(keyframe) if keyframe else ""
            await bilibili.finish(res)
        # 专栏解析
        elif "/read" in url:
            if match := re.search(r"read/cv(\d+)", url):
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
                if "children" in node:
                    for child in node["children"]:
                        text += accumulate_text(child) + " "
                if _text := node.get("text"):
                    text += (
                        _text
                        if isinstance(_text, str)
                        else str(_text) + node.get("url")
                    )
                return text

            for node in data.get("children"):
                node_type = node.get("type")
                if node_type == "ImageNode":
                    if img_url := node.get("url", "").strip():
                        if img_url.startswith("https:https"):
                            img_url = img_url.replace("https:", "", 1)
                        try:
                            img_path = await download_img(img_url)
                        except Exception as e:
                            logger.warning(f"下载图片失败: img_url: {img_url} err: {e}")
                            continue
                        segs.append(MessageSegment.image(img_path))
                elif node_type == "ParagraphNode":
                    if text := accumulate_text(node).strip():
                        segs.append(text)
                elif node_type == "TextNode":
                    segs.append(node.get("text"))

            if segs:
                await bilibili.finish(construct_nodes(bot.self_id, segs))
        # 收藏夹解析
        elif "/favlist" in url:
            # https://space.bilibili.com/22990202/favlist?fid=2344812202
            if match := re.search(r"favlist\?fid=(\d+)", url):
                fav_id = match.group(1)
            else:
                logger.info(f"链接 {url} 无效 - 没有获取到收藏夹 id, 忽略")
                return
            fav_list = (await get_video_favorite_list_content(fav_id))["medias"][:10]
            favs = []
            for fav in fav_list:
                title, cover, intro, link = (
                    fav["title"],
                    fav["cover"],
                    fav["intro"],
                    fav["link"],
                )
                avid = re.search(r"\d+", link).group(0)
                favs.append(
                    MessageSegment.image(cover)
                    + f"🧉 标题：{title}\n📝 简介：{intro}\n🔗 链接：{link}\nhttps://bilibili.com/video/av{avid}"
                )
            await bilibili.send(
                f"{NICKNAME}解析 | 哔哩哔哩 - 收藏夹\n正在为你找出相关链接请稍等..."
            )
            await bilibili.finish(construct_nodes(bot.self_id, favs))
        else:
            logger.warning(f"unsupported url: {url}")
            return
    # 视频
    if keyword in ("av", "/av"):
        v = video.Video(aid=int(video_id), credential=credential)
    else:
        v = video.Video(bvid=video_id, credential=credential)
    # 合并转发消息 list
    segs: list[MessageSegment | str] = []
    try:
        video_info = await v.get_info()
    except Exception as e:
        await bilibili.finish(f"{NICKNAME}解析 | 哔哩哔哩 - 出错 {e}")
    await bilibili.send(f"{NICKNAME}解析 | 哔哩哔哩 - 视频")
    video_title, video_cover, video_desc, video_duration = (
        video_info["title"],
        video_info["pic"],
        video_info["desc"],
        video_info["duration"],
    )
    # 校准 分 p 的情况
    page_num = (int(page_num) - 1) if page_num else 0
    if (pages := video_info.get("pages")) and len(pages) > 1:
        # 解析URL
        if url and (match := re.search(r"(?:&|\?)p=(\d{1,3})", url)):
            page_num = int(match.group(1)) - 1
        # 取模防止数组越界
        page_num = page_num % len(pages)
        p_video = pages[page_num]
        video_duration = p_video.get("duration", video_duration)
        if p_name := p_video.get("part").strip():
            segs.append(f"分集标题: {p_name}")
        if first_frame := p_video.get("first_frame"):
            segs.append(MessageSegment.image(first_frame))
    else:
        page_num = 0
    # 删除特殊字符
    # video_title = delete_boring_characters(video_title)
    online = await v.get_online()
    online_str = (
        f"🏄‍♂️ 总共 {online['total']} 人在观看，{online['count']} 人在网页端观看"
    )
    segs.append(MessageSegment.image(video_cover))
    segs.append(
        f"{video_title}\n{extra_bili_info(video_info)}\n📝 简介：{video_desc}\n{online_str}"
    )
    # 这里是总结内容，如果写了 cookie 就可以
    if credential:
        ai_conclusion = await v.get_ai_conclusion(await v.get_cid(0))
        ai_summary = (
            ai_conclusion.get("model_result", {"summary": ""})
            .get("summary", "")
            .strip()
        )
        ai_summary = f"AI总结: {ai_summary}" if ai_summary else "该视频暂不支持AI总结"
        segs.append(ai_summary)
    if video_duration > DURATION_MAXIMUM:
        segs.append(
            f"⚠️ 当前视频时长 {video_duration // 60} 分钟，超过管理员设置的最长时间 {DURATION_MAXIMUM // 60} 分钟!"
        )
    await bilibili.send(construct_nodes(bot.self_id, segs))
    if video_duration > DURATION_MAXIMUM:
        logger.info(f"video duration > {DURATION_MAXIMUM}, do not download")
        return
    # 下载视频和音频
    try:
        prefix = f"{video_id}-{page_num}"
        video_name = f"{prefix}.mp4"
        video_path = plugin_cache_dir / video_name
        if not video_path.exists():
            download_url_data = await v.get_download_url(page_index=page_num)
            detecter = VideoDownloadURLDataDetecter(download_url_data)
            streams = detecter.detect_best_streams()
            video_url, audio_url = streams[0].url, streams[1].url

            # 下载视频和音频
            v_path, a_path = await asyncio.gather(
                download_file_by_stream(
                    video_url, f"{prefix}-video.m4s", ext_headers=BILIBILI_HEADERS
                ),
                download_file_by_stream(
                    audio_url, f"{prefix}-audio.m4s", ext_headers=BILIBILI_HEADERS
                ),
            )
            await merge_av(v_path, a_path, video_path)
        await bilibili.send(await get_video_seg(video_path))
    except Exception as e:
        if not isinstance(e, ActionFailed):
            await bilibili.send(f"下载视频失败 | {e}")


@bili_music.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    match = re.match(r"^(BV[1-9a-zA-Z]{10})(?:\s)?(\d{1,3})?$", text)
    if not match:
        await bili_music.finish("格式: bm BV1LpD3YsETa [集数](中括号表示可选)")
    await bot.call_api(
        "set_msg_emoji_like", message_id=event.message_id, emoji_id="282"
    )
    bvid, p_num = match.group(1), match.group(2)
    p_num = int(p_num) - 1 if p_num else 0
    v = video.Video(bvid=bvid, credential=credential)
    try:
        video_info = await v.get_info()
        video_title = video_info.get("title")
        if pages := video_info.get("pages"):
            p_num = p_num % len(pages)
            p_video = pages[p_num]
            # video_duration = p_video.get('duration', video_duration)
            if p_name := p_video.get("part").strip():
                video_title = p_name
        video_title = delete_boring_characters(video_title)
        audio_name = f"{video_title}.mp3"
        audio_path = plugin_cache_dir / audio_name
        if not audio_path.exists():
            download_url_data = await v.get_download_url(page_index=p_num)
            detecter = VideoDownloadURLDataDetecter(download_url_data)
            streams = detecter.detect_best_streams()
            audio_url = streams[1].url
            await download_file_by_stream(
                audio_url, audio_name, ext_headers=BILIBILI_HEADERS
            )
    except Exception as e:
        await bili_music.finish(f"download audio excepted err: {e}")
    await bili_music.send(MessageSegment.record(audio_path))
    await bili_music.send(get_file_seg(audio_path))


def extra_bili_info(video_info):
    """
    格式化视频信息
    """
    video_state = video_info["stat"]
    (
        video_like,
        video_coin,
        video_favorite,
        video_share,
        video_view,
        video_danmaku,
        video_reply,
    ) = (
        video_state["like"],
        video_state["coin"],
        video_state["favorite"],
        video_state["share"],
        video_state["view"],
        video_state["danmaku"],
        video_state["reply"],
    )

    video_data_map = {
        "点赞": video_like,
        "硬币": video_coin,
        "收藏": video_favorite,
        "分享": video_share,
        "总播放量": video_view,
        "弹幕数量": video_danmaku,
        "评论": video_reply,
    }

    video_info_result = ""
    for key, value in video_data_map.items():
        if int(value) > 10000:
            formatted_value = f"{value / 10000:.1f}万"
        else:
            formatted_value = value
        video_info_result += f"{key}: {formatted_value} | "

    return video_info_result
