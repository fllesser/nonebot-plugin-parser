import re
import asyncio
from pathlib import Path
from nonebot import on_keyword
from nonebot.log import logger
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Bot, MessageSegment, MessageEvent
from .utils import get_video_seg, construct_nodes
from .filter import is_not_in_disabled_groups

from ..download.common import download_imgs_without_raise
from ..parsers.base import VideoInfo
from ..parsers.douyin import DouYin
from ..config import NICKNAME


douyin = on_keyword(keywords={"douyin.com"}, rule=Rule(is_not_in_disabled_groups))

douyin_parser = DouYin()


@douyin.handle()
async def _(bot: Bot, event: MessageEvent):
    # 消息
    msg: str = event.message.extract_plain_text().strip()
    # 正则匹配
    reg = (
        r"https://(v\.douyin\.com/[a-zA-Z0-9_\-]+|www\.douyin\.com/(video|note)/[0-9]+)"
    )
    matched = re.search(reg, msg)
    if not matched:
        logger.warning("douyin url is incomplete, ignored")
        return
    share_url = matched.group(0)
    share_prefix = f"{NICKNAME}解析 | 抖音 - "
    try:
        video_info: VideoInfo = await douyin_parser.parse_share_url(share_url)
    except Exception as e:
        logger.error(f"Failed to parse douyin url: {share_url}, {e}")
        await douyin.finish("资源直链获取失败, 请联系机器人管理员", reply_message=True)
    await douyin.send(f"{share_prefix}{video_info.title}")
    if video_info.images or video_info.dynamic_images:
        segs = []
        if video_info.images:
            paths: list[Path] = await download_imgs_without_raise(video_info.images)
            segs = [MessageSegment.image(path) for path in paths]
        if video_info.dynamic_images:
            video_tasks = [
                asyncio.create_task(get_video_seg(url=url))
                for url in video_info.dynamic_images
            ]
            video_results = await asyncio.gather(*video_tasks, return_exceptions=True)
            video_seg_lst = [
                seg for seg in video_results if isinstance(seg, MessageSegment)
            ]
            segs = video_seg_lst
        if segs:
            await douyin.finish(construct_nodes(bot.self_id, segs))

    if video_url := video_info.video_url:
        await douyin.finish(await get_video_seg(url=video_url))
