import re

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import KuaishouParser
from .helper import obhelper
from .preprocess import ExtractText, Keyword, on_url_keyword

parser = KuaishouParser()

kuaishou = on_url_keyword("v.kuaishou.com", "kuaishou", "chenzhongtech")

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
        cover_path = await DOWNLOADER.download_img(video_info.cover_url)
        msg += obhelper.img_seg(cover_path)

    await kuaishou.send(msg)
    if video_info.video_url:
        video_path = await DOWNLOADER.download_video(video_info.video_url)
        await kuaishou.send(obhelper.video_seg(video_path))
    if video_info.pic_urls:
        img_paths = await DOWNLOADER.download_imgs_without_raise(video_info.pic_urls)
        segs: list[str | Message | MessageSegment] = [obhelper.img_seg(img_path) for img_path in img_paths]
        assert len(segs) > 0
        await obhelper.send_segments(segs)
