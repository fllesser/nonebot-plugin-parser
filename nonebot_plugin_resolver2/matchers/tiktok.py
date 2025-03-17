import re

import aiohttp
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.log import logger
from nonebot.rule import Rule

from nonebot_plugin_resolver2.config import NICKNAME, PROXY
from nonebot_plugin_resolver2.download.ytdlp import get_video_info, ytdlp_download_video

from .filter import is_not_in_disabled_groups
from .utils import get_video_seg

tiktok = on_keyword(keywords={"tiktok.com"}, rule=Rule(is_not_in_disabled_groups))


@tiktok.handle()
async def _(event: MessageEvent):
    # 消息
    message: str = event.message.extract_plain_text().strip()
    url_reg = r"(?:http:|https:)\/\/(www|vt|vm).tiktok.com\/[A-Za-z\d._?%&+\-=\/#@]*"
    matched = re.search(url_reg, message)
    if not matched:
        logger.warning("tiktok url is incomplete, ignored")
        return
    url, prefix = matched.group(0), matched.group(1)

    if prefix == "vt" or prefix == "vm":
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=False, proxy=PROXY) as resp:
                url = resp.headers.get("Location")
    assert url
    share_prefix = f"{NICKNAME}解析 | TikTok - "
    try:
        info = await get_video_info(url)
        await tiktok.send(f"{share_prefix}{info['title']}")
    except Exception as e:
        await tiktok.send(f"{share_prefix}标题获取出错: {e}")

    try:
        video_path = await ytdlp_download_video(url=url)
        res = await get_video_seg(video_path)
    except Exception as e:
        res = f"{share_prefix}下载视频失败 {e}"

    await tiktok.send(res)
