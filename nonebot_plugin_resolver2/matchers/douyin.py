import asyncio
from pathlib import Path
import re

from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.rule import Rule

from nonebot_plugin_resolver2.config import NICKNAME
from nonebot_plugin_resolver2.download import download_imgs_without_raise
from nonebot_plugin_resolver2.parsers.base import ParseException, VideoInfo
from nonebot_plugin_resolver2.parsers.douyin import DouYin

from .filter import is_not_in_disabled_groups
from .utils import get_video_seg, send_segments

douyin = on_keyword(keywords={"douyin.com"}, rule=Rule(is_not_in_disabled_groups))

douyin_parser = DouYin()


@douyin.handle()
async def _(bot: Bot, event: MessageEvent):
    # 消息
    msg: str = event.message.extract_plain_text().strip()
    # 正则匹配
    reg = r"https://(v\.douyin\.com/[a-zA-Z0-9_\-]+|www\.douyin\.com/(video|note)/[0-9]+)"
    matched = re.search(reg, msg)
    if not matched:
        logger.warning("douyin url is incomplete, ignored")
        return
    share_url = matched.group(0)
    try:
        video_info: VideoInfo = await douyin_parser.parse_share_url(share_url)
    except ParseException:
        await douyin.finish("作品已删除，或资源直链获取失败, 请稍后再试", reply_message=True)
    await douyin.send(f"{NICKNAME}解析 | 抖音 - {video_info.title}")

    segs: list[MessageSegment | Message | str] = []
    if video_info.images:
        paths: list[Path] = await download_imgs_without_raise(video_info.images)
        segs.extend(MessageSegment.image(path) for path in paths)
    if video_info.dynamic_images:
        video_tasks = [asyncio.create_task(get_video_seg(url=url)) for url in video_info.dynamic_images]
        video_results = await asyncio.gather(*video_tasks, return_exceptions=True)
        video_seg_lst = [seg for seg in video_results if isinstance(seg, MessageSegment)]
        segs.extend(video_seg_lst)
    if segs:
        await send_segments(douyin, segs)
        await douyin.finish()
    if video_url := video_info.video_url:
        await douyin.finish(await get_video_seg(url=video_url))
