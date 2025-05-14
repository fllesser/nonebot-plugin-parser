import re

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME, plugin_cache_dir
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
    rule=is_not_in_disabled_groups & r_keywords("kuaishou", "kuaishou.com", "v.kuaishou.com"),
    priority=5,
)

# 匹配的正则表达式
PATTERNS = {
    "kuaishou": re.compile(r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    "kuaishou_short": re.compile(r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    "kuaishou_fw": re.compile(r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
}


@kuaishou.handle()
@handle_exception(kuaishou)
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    """处理快手视频链接"""
    prefix = f"{NICKNAME}解析 | 快手视频 - "
    
    # 尝试匹配链接
    matched_url = None
    for pattern_key, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match:
            matched_url = match.group(0)
            break
            
    if not matched_url:
        logger.info(f"未找到有效的快手链接: {text}")
        return
    

    
    # 解析视频信息
    try:
        video_info = await parser.parse_url(matched_url)
        
        # 下载封面图
        cover_path = await download_img(video_info.cover_url)
        
        # 构建消息段
        segments = [
            f"{prefix}\n{video_info.title}",
            get_img_seg(cover_path)
        ]
        
        # 如果有作者信息，添加到消息中
        if video_info.author:
            segments.append(f"作者: {video_info.author}")
        
        # 发送视频信息
        await send_segments(segments)
        
        # 下载视频
        if video_info.video_url:
            video_path = await download_video(video_info.video_url)
            await kuaishou.send(get_video_seg(video_path))
        else:
            await kuaishou.finish("视频链接获取失败")
            
    except Exception as e:
        logger.error(f"快手视频解析失败: {e}")
        await kuaishou.finish(f"{prefix}解析失败: {str(e)}") 