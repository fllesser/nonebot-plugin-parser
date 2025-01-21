import re
import httpx
import json
import asyncio

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.plugin.on import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from urllib.parse import parse_qs, urlparse

from .filter import is_not_in_disable_group
from .utils import get_video_seg, construct_nodes
from .preprocess import r_keywords, R_EXTRACT_KEY

from ..constant import COMMON_HEADER
from ..download.common import download_img
from ..config import rconfig, NICKNAME

# 小红书下载链接
XHS_REQ_LINK = "https://www.xiaohongshu.com/explore/"

xiaohongshu = on_message(
    rule=is_not_in_disable_group & r_keywords("xiaohongshu.com", "xhslink.com")
)


@xiaohongshu.handle()
async def _(bot: Bot, state: T_State):
    text = state.get(R_EXTRACT_KEY)

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
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            url = str(resp.url)
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
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{XHS_REQ_LINK}{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}",
            headers=headers,
        )
        html = resp.text
    pattern = r"window.__INITIAL_STATE__=(.*?)</script>"
    if match := re.search(pattern, html):
        json_str = match.group(1)
    else:
        await xiaohongshu.finish("小红书 cookie 可能已失效")
    json_str = json_str.replace("undefined", "null")
    json_obj = json.loads(json_str)
    note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
    type = note_data["type"]
    note_title = note_data["title"]
    note_desc = note_data["desc"]
    title_msg = f"{NICKNAME}解析 | 小红书 - {note_title}\n{note_desc}"

    if type == "normal":
        aio_task = []
        image_list = note_data["imageList"]
        # 批量
        for index, item in enumerate(image_list):
            aio_task.append(asyncio.create_task(download_img(item["urlDefault"])))
        img_path_list = await asyncio.gather(*aio_task)
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
