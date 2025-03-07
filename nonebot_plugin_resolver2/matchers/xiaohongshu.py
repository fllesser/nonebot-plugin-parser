import re
import json
import aiohttp

from nonebot.log import logger
from nonebot.plugin.on import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from urllib.parse import parse_qs, urlparse

from .filter import is_not_in_disabled_groups
from .utils import get_video_seg, construct_nodes
from .preprocess import r_keywords, ExtractText

from ..constant import COMMON_HEADER
from ..download.common import download_imgs_without_raise
from ..config import rconfig, NICKNAME

# 小红书下载链接
XHS_REQ_LINK = "https://www.xiaohongshu.com/explore/"

xiaohongshu = on_message(
    rule=is_not_in_disabled_groups & r_keywords("xiaohongshu.com", "xhslink.com")
)


@xiaohongshu.handle()
async def _(bot: Bot, text: str = ExtractText()):
    share_prefix = f"{NICKNAME}解析 | 小红书 - "

    if match := re.search(
        r"(http:|https:)\/\/(xhslink|(www\.)xiaohongshu).com\/[A-Za-z\d._?%&+\-=\/#@]*",
        text,
    ):
        url = match.group(0)
    else:
        logger.info(f"{text} ignored")
        return
    # 请求头
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.9",
        "cookie": rconfig.r_xhs_ck,
    } | COMMON_HEADER
    if "xhslink" in url:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, allow_redirects=False) as resp:
                url = resp.headers.get("Location", "")
    # ?: 非捕获组
    pattern = r"(?:/explore/|/discovery/item/|source=note&noteId=)(\w+)"
    if match := re.search(pattern, url):
        xhs_id = match.group(1)
    else:
        return
    # 解析 URL 参数
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    # 提取 xsec_source 和 xsec_token
    xsec_source = params.get("xsec_source", [None])[0] or "pc_feed"
    xsec_token = params.get("xsec_token", [None])[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{XHS_REQ_LINK}{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}",
            headers=headers,
        ) as resp:
            html = await resp.text()
    pattern = r"window.__INITIAL_STATE__=(.*?)</script>"
    if match := re.search(pattern, html):
        json_str = match.group(1)
    else:
        await xiaohongshu.finish(f"{share_prefix} cookies 可能已失效")
    json_str = json_str.replace("undefined", "null")
    json_obj = json.loads(json_str)
    note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
    type = note_data["type"]
    note_title = note_data["title"]
    note_desc = note_data["desc"]
    title_msg = f"{share_prefix}{note_title}\n{note_desc}"

    if type == "normal":
        image_list = note_data["imageList"]
        urls = [item["urlDefault"] for item in image_list]
        img_path_list = await download_imgs_without_raise(urls)
        # 发送图片
        segs = [title_msg] + [
            MessageSegment.image(img_path) for img_path in img_path_list
        ]
        nodes = construct_nodes(bot.self_id, segs)
        await xiaohongshu.finish(nodes)
    elif type == "video":
        await xiaohongshu.send(title_msg)
        # 这是一条解析有水印的视频
        # logger.info(note_data['video'])
        video_url = note_data["video"]["media"]["stream"]["h264"][0]["masterUrl"]
        # video_url = f"http://sns-video-bd.xhscdn.com/{note_data['video']['consumer']['originVideoKey']}"
        await xiaohongshu.finish(await get_video_seg(url=video_url))
