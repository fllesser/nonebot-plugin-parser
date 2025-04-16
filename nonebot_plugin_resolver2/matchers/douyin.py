import asyncio
from pathlib import Path
import re

from nonebot import logger, on_keyword
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.rule import Rule

from ..config import NICKNAME
from ..download import download_imgs_without_raise, download_video
from ..exception import handle_exception
from ..parsers import DouyinParser
from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg, send_segments

douyin = on_keyword(keywords={"douyin.com"}, rule=Rule(is_not_in_disabled_groups))

douyin_parser = DouyinParser()


@douyin.handle()
@handle_exception(douyin)
async def _(event: MessageEvent):
    # 消息
    msg: str = event.message.extract_plain_text().strip()
    # 正则匹配
    reg = r"https://(v\.douyin\.com/[a-zA-Z0-9_\-]+|www\.douyin\.com/(video|note)/[0-9]+)"
    matched = re.search(reg, msg)
    if not matched:
        logger.warning("douyin url is incomplete, ignored")
        return
    share_url = matched.group(0)
    video_info = await douyin_parser.parse_share_url(share_url)
    await douyin.send(f"{NICKNAME}解析 | 抖音 - {video_info.title}")

    segs: list[MessageSegment | Message | str] = []
    # 存在普通图片
    if video_info.pic_urls:
        paths: list[Path] = await download_imgs_without_raise(video_info.pic_urls)
        segs.extend(get_img_seg(path) for path in paths)
    # 存在动态图片
    if video_info.dynamic_urls:
        # 并发下载动态图片
        video_download_tasks = [asyncio.create_task(download_video(url)) for url in video_info.dynamic_urls]
        video_download_results = await asyncio.gather(*video_download_tasks, return_exceptions=True)
        video_seg_lst = [get_video_seg(seg) for seg in video_download_results if isinstance(seg, Path)]
        segs.extend(video_seg_lst)
    if segs:
        await send_segments(segs)
        await douyin.finish()
    # 存在视频
    if video_url := video_info.video_url:
        video_path = await download_video(video_url)
        await douyin.finish(get_video_seg(video_path))
