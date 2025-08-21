import re

import httpx
from nonebot import logger

from ..config import NICKNAME
from ..constants import COMMON_TIMEOUT
from ..download.ytdlp import get_video_info, ytdlp_download_video
from ..exception import handle_exception
from .helper import obhelper
from .preprocess import KeyPatternMapping, KeyPatternMatched, on_keyword_regex

KEY_PATTERN_MAPPING = KeyPatternMapping(
    ("tiktok.com", r"(?:http:|https:)\/\/(www|vt|vm).tiktok.com\/[A-Za-z\d._?%&+\-=\/#@]*"),
)

tiktok = on_keyword_regex(KEY_PATTERN_MAPPING)


@tiktok.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    # 提取 url 和 prefix
    url, prefix = searched.group(0), searched.group(1)

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

    await tiktok.send(obhelper.video_seg(video_path))
