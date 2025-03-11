import re

from bilibili_api import Credential, select_client
from bilibili_api.article import Article
from bilibili_api.favorite_list import get_video_favorite_list_content
from bilibili_api.live import LiveRoom
from bilibili_api.opus import Opus

from nonebot_plugin_resolver2.config import rconfig
from nonebot_plugin_resolver2.cookie import cookies_str_to_dict

CREDENTIAL: Credential | None = (
    Credential.from_cookies(cookies_str_to_dict(rconfig.r_bili_ck)) if rconfig.r_bili_ck else None
)

# 选择客户端
select_client("curl_cffi")
# 模仿浏览器
# request_settings.set("impersonate", "chrome131")


async def parse_opus(opus_id: int) -> tuple[list[str], str]:
    opus = Opus(opus_id, CREDENTIAL)
    opus_info = await opus.get_info()
    if not isinstance(opus_info, dict):
        raise Exception("获取动态信息失败")

    # 递归查找 opus_info 里所有键为 url 的 value
    def find_url(d: dict):
        for k, v in d.items():
            if k == "url":
                yield v
            if isinstance(v, dict):
                yield from find_url(v)
            if isinstance(v, list):
                for i in v:
                    if isinstance(i, dict):
                        yield from find_url(i)

    urls = list(find_url(opus_info))

    dynamic = opus.turn_to_dynamic()
    dynamic_info = await dynamic.get_info()
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
    room = LiveRoom(room_display_id=room_id, credential=CREDENTIAL)
    room_info = (await room.get_room_info())["room_info"]
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
    fav_list = (await get_video_favorite_list_content(fav_id))["medias"][:50]
    texts = []
    urls = []
    for fav in fav_list:
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


async def parse_video_info(*, bvid: str | None = None, avid: int | None = None) -> None:
    pass


async def parse_video_download_url(
    *, bvid: str | None = None, avid: int | None = None, page_index: int = 0
) -> tuple[str, str]:
    from bilibili_api.video import Video, VideoDownloadURLDataDetecter

    if avid:
        video = Video(aid=avid, credential=CREDENTIAL)
    elif bvid:
        video = Video(bvid=bvid, credential=CREDENTIAL)
    else:
        raise ValueError("avid 和 bvid 至少指定一项")
    # 获取下载数据
    download_url_data = await video.get_download_url(page_index=page_index)
    detecter = VideoDownloadURLDataDetecter(download_url_data)
    streams = detecter.detect_best_streams()
    video_stream = streams[0]
    audio_stream = streams[1]
    if video_stream is None or audio_stream is None:
        raise ValueError("未找到视频或音频流")
    return video_stream.url, audio_stream.url
