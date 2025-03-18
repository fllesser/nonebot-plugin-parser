import re
from typing import Any

import aiohttp
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.plugin.on import on_keyword
from nonebot.rule import Rule

from nonebot_plugin_resolver2.config import NICKNAME, PROXY
from nonebot_plugin_resolver2.constant import COMMON_HEADER
from nonebot_plugin_resolver2.download import download_img

from .filter import is_not_in_disabled_groups
from .utils import get_video_seg

twitter = on_keyword(keywords={"x.com"}, rule=Rule(is_not_in_disabled_groups))


@twitter.handle()
async def _(event: MessageEvent):
    msg: str = event.message.extract_plain_text().strip()

    if match := re.search(r"https?:\/\/x.com\/[0-9-a-zA-Z_]{1,20}\/status\/([0-9]*)", msg):
        x_url = match.group(0)
    else:
        return
    x_url = f"http://47.99.158.118/video-crack/v2/parse?content={x_url}"

    # 内联一个请求
    async def x_req(url: str) -> dict[str, Any]:
        headers = {
            "Accept": "ext/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Host": "47.99.158.118",
            "Proxy-Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            **COMMON_HEADER,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return await response.json()

    resp = await x_req(x_url)
    x_data = resp.get("data")

    await twitter.send(f"{NICKNAME}解析 | 小蓝鸟")

    if x_data is not None:
        x_video_url = x_data["url"]
        await twitter.send(await get_video_seg(url=x_video_url, proxy=PROXY))
    else:
        resp = await x_req(f"{x_url}/photo")
        x_pic_url = resp["data"]["url"]
        img_path = await download_img(url=x_pic_url, proxy=PROXY)
        await twitter.send(MessageSegment.image(img_path))
