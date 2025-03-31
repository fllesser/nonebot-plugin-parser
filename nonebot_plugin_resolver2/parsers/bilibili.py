from dataclasses import dataclass
import re
from typing import Any

from bilibili_api import Credential
from bilibili_api.video import Video

from .base import ParseException

CREDENTIAL: Credential | None = None


def init_bilibili_api():
    """初始化 bilibili api"""

    from bilibili_api import request_settings, select_client

    from ..config import rconfig
    from ..cookie import cookies_str_to_dict

    # 选择客户端
    select_client("curl_cffi")
    # 模仿浏览器
    request_settings.set("impersonate", "chrome131")
    # 第二参数数值参考 curl_cffi 文档
    # https://curl-cffi.readthedocs.io/en/latest/impersonate.html
    global CREDENTIAL
    CREDENTIAL = Credential.from_cookies(cookies_str_to_dict(rconfig.r_bili_ck)) if rconfig.r_bili_ck else None


async def parse_opus(opus_id: int) -> tuple[list[str], str]:
    """解析动态信息

    Args:
        opus_id (int): 动态 id

    Returns:
        tuple[list[str], str]: 图片 url 列表和动态信息
    """
    from bilibili_api.opus import Opus

    opus = Opus(opus_id, CREDENTIAL)
    opus_info = await opus.get_info()
    if not isinstance(opus_info, dict):
        raise ParseException("获取动态信息失败")

    # 获取图片信息
    urls = await opus.get_images_raw_info()
    urls = [url["url"] for url in urls]

    dynamic = opus.turn_to_dynamic()
    dynamic_info: dict[str, Any] = await dynamic.get_info()
    orig_text = (
        dynamic_info.get("item", {})
        .get("modules", {})
        .get("module_dynamic", {})
        .get("major", {})
        .get("opus", {})
        .get("summary", {})
        .get("rich_text_nodes", [{}])[0]
        .get("orig_text", "")
    )
    return urls, orig_text


async def parse_live(room_id: int) -> tuple[str, str, str]:
    """解析直播信息

    Args:
        room_id (int): 直播 id

    Returns:
        tuple[str, str, str]: 标题、封面、关键帧
    """
    from bilibili_api.live import LiveRoom

    room = LiveRoom(room_display_id=room_id, credential=CREDENTIAL)
    room_info: dict[str, Any] = (await room.get_room_info())["room_info"]
    title, cover, keyframe = (
        room_info["title"],
        room_info["cover"],
        room_info["keyframe"],
    )
    return (title, cover, keyframe)


async def parse_read(read_id: int) -> tuple[list[str], list[str]]:
    """专栏解析

    Args:
        read_id (int): 专栏 id

    Returns:
        list[str]: img url or text
    """
    from bilibili_api.article import Article

    ar = Article(read_id)

    # 加载内容
    await ar.fetch_content()
    data = ar.json()

    def accumulate_text(node: dict):
        text = ""
        if "children" in node:
            for child in node["children"]:
                text += accumulate_text(child) + " "
        if _text := node.get("text"):
            text += _text if isinstance(_text, str) else str(_text) + node["url"]
        return text

    urls: list[str] = []
    texts: list[str] = []
    for node in data.get("children", []):
        node_type = node.get("type")
        if node_type == "ImageNode":
            if img_url := node.get("url", "").strip():
                urls.append(img_url)
                # 补空串占位符
                texts.append("")
        elif node_type == "ParagraphNode":
            if text := accumulate_text(node).strip():
                texts.append(text)
        elif node_type == "TextNode":
            if text := node.get("text", "").strip():
                texts.append(text)
    return texts, urls


async def parse_favlist(fav_id: int) -> tuple[list[str], list[str]]:
    """解析收藏夹信息

    Args:
        fav_id (int): 收藏夹 id

    Returns:
        tuple[list[str], list[str]]: 标题、封面、简介、链接
    """
    from bilibili_api.favorite_list import get_video_favorite_list_content

    fav_list: dict[str, Any] = await get_video_favorite_list_content(fav_id)
    # 取前 50 个
    medias_50: list[dict[str, Any]] = fav_list["medias"][:50]
    texts: list[str] = []
    urls: list[str] = []
    for fav in medias_50:
        title, cover, intro, link = (
            fav["title"],
            fav["cover"],
            fav["intro"],
            fav["link"],
        )
        matched = re.search(r"\d+", link)
        if not matched:
            continue
        avid = matched.group(0) if matched else ""
        urls.append(cover)
        texts.append(f"🧉 标题：{title}\n📝 简介：{intro}\n🔗 链接：{link}\nhttps://bilibili.com/video/av{avid}")
    return texts, urls


@dataclass
class BilibiliVideoInfo:
    """Bilibili 视频信息"""

    title: str
    display_info: str
    cover_url: str
    video_duration: int
    video_url: str
    audio_url: str
    ai_summary: str


def parse_video(*, bvid: str | None = None, avid: int | None = None) -> Video:
    """解析视频信息

    Args:
        bvid (str | None): bvid
        avid (int | None): avid
    """
    if avid:
        return Video(aid=avid, credential=CREDENTIAL)
    elif bvid:
        return Video(bvid=bvid, credential=CREDENTIAL)
    else:
        raise ParseException("avid 和 bvid 至少指定一项")


async def parse_video_info(*, bvid: str | None = None, avid: int | None = None, page_num: int = 1) -> BilibiliVideoInfo:
    """解析视频信息

    Args:
        bvid (str | None): bvid
        avid (int | None): avid
        page_num (int): 页码
    """

    video = parse_video(bvid=bvid, avid=avid)
    video_info: dict[str, Any] = await video.get_info()

    video_duration: int = int(video_info["duration"])

    display_info: str = ""
    cover_url: str | None = None
    title: str = video_info["title"]
    # 处理分 p
    page_idx = page_num - 1
    if (pages := video_info.get("pages")) and len(pages) > 1:
        assert isinstance(pages, list)
        # 取模防止数组越界
        page_idx = page_idx % len(pages)
        p_video = pages[page_idx]
        # 获取分集时长
        video_duration = int(p_video.get("duration", video_duration))
        # 获取分集标题
        if p_name := p_video.get("part").strip():
            title += f"\n分集: {p_name}"
        # 获取分集封面
        if first_frame_url := p_video.get("first_frame"):
            cover_url = first_frame_url
    else:
        page_idx = 0

    # 获取下载链接
    video_url, audio_url = await parse_video_download_url(video=video, page_index=page_idx)
    # 获取在线观看人数
    online = await video.get_online()

    display_info = (
        f"{__extra_bili_info(video_info)}\n"
        f"📝 简介：{video_info['desc']}\n"
        f"🏄‍♂️ 总共 {online['total']} 人在观看，{online['count']} 人在网页端观看"
    )
    ai_summary: str = "未配置 ck 无法使用 AI 总结"
    # 获取 AI 总结
    if CREDENTIAL:
        cid = await video.get_cid(page_idx)
        ai_conclusion = await video.get_ai_conclusion(cid)
        ai_summary = ai_conclusion.get("model_result", {"summary": ""}).get("summary", "").strip()
        ai_summary = f"AI总结: {ai_summary}" if ai_summary else "该视频暂不支持AI总结"

    return BilibiliVideoInfo(
        title=title,
        display_info=display_info,
        cover_url=cover_url if cover_url else video_info["pic"],
        video_url=video_url,
        audio_url=audio_url,
        video_duration=video_duration,
        ai_summary=ai_summary,
    )


async def parse_video_download_url(
    *, video: Video | None = None, bvid: str | None = None, avid: int | None = None, page_index: int = 0
) -> tuple[str, str]:
    """解析视频下载链接

    Args:
        bvid (str | None): bvid
        avid (int | None): avid
        page_index (int): 页索引 = 页码 - 1
    """

    from bilibili_api.video import VideoDownloadURLDataDetecter

    if video is None:
        video = parse_video(bvid=bvid, avid=avid)
    # 获取下载数据
    download_url_data = await video.get_download_url(page_index=page_index)
    detecter = VideoDownloadURLDataDetecter(download_url_data)
    streams = detecter.detect_best_streams()
    video_stream = streams[0]
    audio_stream = streams[1]
    if video_stream is None or audio_stream is None:
        raise ValueError("未找到视频或音频流")
    return video_stream.url, audio_stream.url


def __extra_bili_info(video_info: dict[str, Any]) -> str:
    """
    格式化视频信息
    """
    # 获取视频统计数据
    video_state: dict[str, Any] = video_info["stat"]

    # 定义需要展示的数据及其显示名称
    stats_mapping = [
        ("点赞", "like"),
        ("硬币", "coin"),
        ("收藏", "favorite"),
        ("分享", "share"),
        ("评论", "reply"),
        ("总播放量", "view"),
        ("弹幕数量", "danmaku"),
    ]

    # 构建结果字符串
    result_parts = []
    for display_name, stat_key in stats_mapping:
        value = video_state[stat_key]
        # 数值超过10000时转换为万为单位
        formatted_value = f"{value / 10000:.1f}万" if value > 10000 else str(value)
        result_parts.append(f"{display_name}: {formatted_value}")

    return " | ".join(result_parts)
