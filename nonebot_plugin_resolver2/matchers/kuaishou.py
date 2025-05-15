import re

from nonebot import logger, on_message

from ..config import NICKNAME
from ..download import download_img, download_video
from ..exception import handle_exception
from ..parsers import KuaishouParser
from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg
from .preprocess import ExtractText, Keyword, r_keywords

# 初始化快手解析器
parser = KuaishouParser()


# 定义匹配规则
kuaishou = on_message(
    rule=is_not_in_disabled_groups & r_keywords("v.kuaishou.com", "kuaishou", "chenzhongtech"),
    priority=5,
)


# 匹配的正则表达式
PATTERNS = {
    # - https://v.kuaishou.com/1ff8QP （该短链接失效）
    "v.kuaishou.com": re.compile(r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    # - https://www.kuaishou.com/short-video/3xhjgcmir24m4nm
    "kuaishou": re.compile(r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    # - https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc
    "chenzhongtech": re.compile(r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
}


@kuaishou.handle()
@handle_exception(kuaishou)
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    """处理快手视频链接"""
    prefix = f"{NICKNAME}解析 | 快手 - "

    matched = PATTERNS[keyword].search(text)
    if not matched:
        logger.info(f"无有效的快手链接: {text}")
        return

    url = matched.group(0)

    logger.debug(f"开始解析快手链接: {url}")
    video_info = await parser.parse_url(url)
    logger.debug(f"快手视频标题: {video_info.title}")

    msg = f"{prefix}{video_info.title}-{video_info.author}"
    if video_info.cover_url:
        # 下载封面
        cover_path = await download_img(video_info.cover_url)
        msg += get_img_seg(cover_path)
    await kuaishou.send(msg)
    video_path = await download_video(video_info.video_url)
    await kuaishou.send(get_video_seg(video_path))
