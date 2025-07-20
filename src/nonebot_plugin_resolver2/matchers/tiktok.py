import re

import httpx
from nonebot import logger, on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule

from ..config import NICKNAME
from ..constant import COMMON_TIMEOUT
from ..download.ytdlp import get_video_info, ytdlp_download_video
from ..exception import handle_exception
from .filter import is_not_in_disabled_groups
from .helper import obhelper

tiktok = on_keyword(keywords={"tiktok.com"}, rule=Rule(is_not_in_disabled_groups))


@tiktok.handle()
@handle_exception()
async def _(event: MessageEvent):
    # 消息
    message: str = event.message.extract_plain_text().strip()
    url_reg = r"(?:http:|https:)\/\/(www|vt|vm).tiktok.com\/[A-Za-z\d._?%&+\-=\/#@]*"
    matched = re.search(url_reg, message)
    if not matched:
        logger.warning("tiktok url is incomplete, ignored")
        await tiktok.finish()
    # 提取 url 和 prefix
    url, prefix = matched.group(0), matched.group(1)

    # 如果 prefix 是 vt 或 vm，则需要重定向
    if prefix == "vt" or prefix == "vm":
        async with httpx.AsyncClient(follow_redirects=True, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            url = response.headers.get("Location")

    pub_prefix = f"{NICKNAME}解析 | TikTok - "
    if not url:
        await tiktok.finish(f"{pub_prefix}短链重定向失败")

    # 获取视频信息
    info = await get_video_info(url)
    await tiktok.send(f"{pub_prefix}{info['title']}")

    try:
        video_path = await ytdlp_download_video(url=url)
    except Exception:
        logger.error(f"tiktok video download failed | {url}", exc_info=True)
        await tiktok.finish(f"{pub_prefix}下载视频失败")

    await tiktok.send(obhelper.get_video_seg(video_path))
