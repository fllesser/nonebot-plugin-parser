import asyncio
from pathlib import Path
import re

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import DouyinParser
from .helper import obhelper
from .preprocess import ExtractText, Keyword, on_url_keyword

douyin = on_url_keyword("v.douyin", "douyin")

parser = DouyinParser()

PATTERNS: dict[str, re.Pattern] = {
    "v.douyin": re.compile(r"https://v\.douyin\.com/[a-zA-Z0-9_\-]+"),
    "douyin": re.compile(r"https://www\.(?:douyin|iesdouyin)\.com/(?:video|note|share/(?:video|note|slides))/[0-9]+"),
}


@douyin.handle()
@handle_exception()
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    # 正则匹配
    matched = PATTERNS[keyword].search(text)
    if not matched:
        logger.warning(f"{text} 中的链接无效, 忽略")
        return
    share_url = matched.group(0)
    parse_result = await parser.parse_share_url(share_url)
    await douyin.send(f"{NICKNAME}解析 | 抖音 - {parse_result.title}")

    segs: list[MessageSegment | Message | str] = []
    # 存在普通图片
    if pic_urls := parse_result.pic_urls:
        paths = await DOWNLOADER.download_imgs_without_raise(pic_urls)
        segs.extend(obhelper.img_seg(path) for path in paths)

    # 存在动态图片
    if dynamic_urls := parse_result.dynamic_urls:
        # 并发下载动态图片
        video_paths = await asyncio.gather(
            *[DOWNLOADER.download_video(url) for url in dynamic_urls], return_exceptions=True
        )
        video_segs = [obhelper.video_seg(p) for p in video_paths if isinstance(p, Path)]
        segs.extend(video_segs)

    if segs:
        await obhelper.send_segments(segs)
        await douyin.finish()

    # 存在视频
    if video_url := parse_result.video_url:
        video_path = await DOWNLOADER.download_video(video_url)
        await douyin.finish(obhelper.video_seg(video_path))
