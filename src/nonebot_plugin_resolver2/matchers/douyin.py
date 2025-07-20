import asyncio
from pathlib import Path
import re

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME
from ..download import stream_downloader
from ..exception import handle_exception
from ..parsers import DouyinParser
from .filter import is_not_in_disabled_groups
from .helper import OnebotHelper
from .preprocess import ExtractText, Keyword, r_keywords

# douyin = on_keyword(keywords={"douyin.com"}, rule=Rule(is_not_in_disabled_groups))
douyin = on_message(rule=is_not_in_disabled_groups & r_keywords("v.douyin", "douyin"))
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
    if parse_result.pic_urls:
        paths = await stream_downloader.download_imgs_without_raise(parse_result.pic_urls)
        segs.extend(OnebotHelper.get_img_seg(path) for path in paths)
    # 存在动态图片
    if parse_result.dynamic_urls:
        # 并发下载动态图片
        video_paths = await asyncio.gather(
            *[stream_downloader.download_video(url) for url in parse_result.dynamic_urls], return_exceptions=True
        )
        video_segs = [OnebotHelper.get_video_seg(p) for p in video_paths if isinstance(p, Path)]
        segs.extend(video_segs)
    if segs:
        await OnebotHelper.send_segments(segs)
        await douyin.finish()
    # 存在视频
    if video_url := parse_result.video_url:
        video_path = await stream_downloader.download_video(video_url)
        await douyin.finish(OnebotHelper.get_video_seg(video_path))
