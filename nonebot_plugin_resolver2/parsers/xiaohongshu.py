import json
import re
from urllib.parse import parse_qs, urlparse

import aiohttp

from nonebot_plugin_resolver2.config import rconfig
from nonebot_plugin_resolver2.constant import COMMON_HEADER

# 小红书下载链接
XHS_REQ_LINK = "https://www.xiaohongshu.com/explore/"


async def parse_url(url: str) -> tuple[str, list[str], str]:
    """
    解析小红书 URL
    """
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
    matched = re.search(pattern, url)
    if not matched:
        raise Exception("没有符合的小红书 URL")
    xhs_id = matched.group(1)
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
    matched = re.search(pattern, html)
    if not matched:
        raise Exception("小红书 cookies 可能已失效")

    json_str = matched.group(1)
    json_str = json_str.replace("undefined", "null")
    json_obj = json.loads(json_str)

    note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
    # 资源类型 normal 图，video 视频
    resource_type = note_data["type"]
    # 标题
    note_title = note_data["title"]
    # 描述
    note_desc = note_data["desc"]
    title_desc = f"{note_title}\n{note_desc}"
    img_urls: list[str] = []
    video_url: str = ""
    if resource_type == "normal":
        image_list = note_data["imageList"]
        img_urls = [item["urlDefault"] for item in image_list]
    elif resource_type == "video":
        video_url = note_data["video"]["media"]["stream"]["h264"][0]["masterUrl"]
    return title_desc, img_urls, video_url
