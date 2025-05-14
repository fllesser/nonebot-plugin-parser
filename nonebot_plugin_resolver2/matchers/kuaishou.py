import re

from nonebot import logger, on_message

from ..config import NICKNAME
from ..download import download_img, download_video
from ..exception import handle_exception
from ..parsers import KuaishouParser
from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg, send_segments
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
    "v.kuaishou.com": re.compile(r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    "kuaishou": re.compile(r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    "chenzhongtech": re.compile(r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
}


@kuaishou.handle()
@handle_exception(kuaishou)
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    """处理快手视频链接"""
    prefix = f"{NICKNAME}解析 | 快手视频 - "

    matched = PATTERNS[keyword].search(text)
    if not matched:
        logger.info(f"未找到有效的快手链接: {text}")
        return

    url = matched.group(0)

    logger.debug(f"开始解析快手链接: {url}")
    video_info = await parser.parse_url(url)
    logger.debug(f"快手视频标题: {video_info.title}")

    # 构建消息段列表，确保类型正确
    segments = []
    segments.append(f"{prefix}{video_info.title}")

    # 下载封面图
    if video_info.cover_url:
        logger.debug(f"开始下载快手视频封面: {video_info.cover_url}")
        cover_path = await download_img(video_info.cover_url)
        logger.debug(f"封面下载完成: {cover_path}")
        # 添加图片消息段
        segments.append(get_img_seg(cover_path))
    else:
        logger.warning("未获取到视频封面URL")

    # 如果有作者信息，添加到消息中
    if video_info.author:
        segments.append(f"作者: {video_info.author}")

    # 发送视频信息
    await send_segments(segments)

    # 下载视频
    if video_info.video_url:
        logger.debug(f"开始下载快手视频: {video_info.video_url}")
        video_path = await download_video(video_info.video_url)
        logger.debug(f"视频下载完成: {video_path}")
        await kuaishou.send(get_video_seg(video_path))
    else:
        logger.warning("未获取到视频URL")
        await kuaishou.finish("视频链接获取失败")
