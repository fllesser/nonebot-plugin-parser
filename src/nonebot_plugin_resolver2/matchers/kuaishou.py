import re

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME
from ..download import download_img, download_imgs_without_raise, download_video
from ..exception import handle_exception
from ..parsers import KuaishouParser
from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg, send_segments
from .preprocess import ExtractText, Keyword, r_keywords

parser = KuaishouParser()

kuaishou = on_message(
    rule=is_not_in_disabled_groups & r_keywords("v.kuaishou.com", "kuaishou", "chenzhongtech"),
    priority=5,
)


# 匹配的正则表达式
PATTERNS = {
    # - https://v.kuaishou.com/2yAnzeZ
    "v.kuaishou.com": re.compile(r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    # - https://www.kuaishou.com/short-video/3xhjgcmir24m4nm
    "kuaishou": re.compile(r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    # - https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc
    "chenzhongtech": re.compile(r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
}


@kuaishou.handle()
@handle_exception()
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    """处理快手视频链接"""
    matched = PATTERNS[keyword].search(text)
    if not matched:
        logger.info(f"无有效的快手链接: {text}")
        return

    url = matched.group(0)

    video_info = await parser.parse_url(url)

    msg = f"{NICKNAME}解析 | 快手 - {video_info.title}-{video_info.author}"
    if video_info.cover_url:
        # 下载封面
        cover_path = await download_img(video_info.cover_url)
        msg += get_img_seg(cover_path)

    await kuaishou.send(msg)
    if video_info.video_url:
        video_path = await download_video(video_info.video_url)
        await kuaishou.send(get_video_seg(video_path))
    if video_info.pic_urls:
        img_paths = await download_imgs_without_raise(video_info.pic_urls)
        segs: list[str | Message | MessageSegment] = [get_img_seg(img_path) for img_path in img_paths]
        assert len(segs) > 0
        await send_segments(segs)
