from bilibili_api import Credential, select_client
from bilibili_api.opus import Opus
from bilibili_api.live import LiveRoom
from bilibili_api.article import Article
from ..config import rconfig
from ..cookie import cookies_str_to_dict

CREDENTIAL: Credential | None = (
    Credential.from_cookies(cookies_str_to_dict(rconfig.r_bili_ck))
    if rconfig.r_bili_ck
    else None
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
    return (urls, orig_text)


async def parse_live(room_id: int) -> tuple[str, str, str]:
    room = LiveRoom(room_display_id=room_id, credential=CREDENTIAL)
    room_info = (await room.get_room_info())["room_info"]
    title, cover, keyframe = (
        room_info["title"],
        room_info["cover"],
        room_info["keyframe"],
    )
    return (f"直播 - {title}", cover, keyframe)


async def parse_read(read_id: int) -> list[str]:
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

    text_or_url_lst: list[str] = []
    for node in data.get("children", []):
        node_type = node.get("type")
        if node_type == "ImageNode":
            if img_url := node.get("url", "").strip():
                text_or_url_lst.append(img_url)
        elif node_type == "ParagraphNode":
            if text := accumulate_text(node).strip():
                text_or_url_lst.append(text)
        elif node_type == "TextNode":
            if text := node.get("text", "").strip():
                text_or_url_lst.append(text)
    return text_or_url_lst


async def parse_video(bvid: str | None = None, avid: int | None = None):
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    res = asyncio.run(parse_read(523868))
    print(res)
