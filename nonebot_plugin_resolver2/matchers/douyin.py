import re
import asyncio

from nonebot import on_keyword
from nonebot.log import logger
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Event, Bot, MessageSegment
from .utils import get_video_seg, construct_nodes
from .filter import is_not_in_disable_group

from ..download.common import download_img
from ..parsers.base import VideoInfo
from ..parsers.douyin import DouYin
from ..config import NICKNAME


douyin = on_keyword(keywords={"douyin.com"}, rule=Rule(is_not_in_disable_group))

douyin_parser = DouYin()


@douyin.handle()
async def _(bot: Bot, event: Event):
    # 消息
    msg: str = event.message.extract_plain_text().strip()
    # 正则匹配
    reg = r"https://(v\.douyin\.com/[a-zA-Z0-9]+|www\.douyin\.com/video/[0-9]+)"
    if match := re.search(reg, msg):
        share_url = match.group(0)
    else:
        logger.info("douyin url is incomplete, ignored")
        return
    try:
        video_info: VideoInfo = await douyin_parser.parse_share_url(share_url)
    except Exception as e:
        await douyin.finish(f"{NICKNAME}解析 | 抖音 - {e}")
    await douyin.send(f"{NICKNAME}解析 | 抖音 - {video_info.title}")
    if video_info.images or video_info.dynamic_images:
        segs = []
        if video_info.images:
            img_tasks = [
                asyncio.create_task(download_img(url)) for url in video_info.images
            ]
            img_path_list = await asyncio.gather(*img_tasks)
            segs.extend([MessageSegment.image(img_path) for img_path in img_path_list])
        if video_info.dynamic_images:
            video_tasks = [
                asyncio.create_task(get_video_seg(url=url))
                for url in video_info.dynamic_images
            ]
            video_seg_list = await asyncio.gather(*video_tasks)
            segs.extend(video_seg_list)
        await douyin.finish(construct_nodes(bot.self_id, segs))

    if video_url := video_info.video_url:
        await douyin.finish(await get_video_seg(url=video_url))
