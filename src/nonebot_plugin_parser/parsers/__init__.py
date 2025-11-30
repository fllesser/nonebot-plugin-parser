# 导出所有 Parser 类
from .nga import NGAParser as NGAParser
from .base import BaseParser as BaseParser
from .acfun import AcfunParser as AcfunParser
from .weibo import WeiBoParser as WeiBoParser
from .douyin import DouyinParser as DouyinParser
from .twitter import TwitterParser as TwitterParser
from .bilibili import BilibiliParser as BilibiliParser
from .kuaishou import KuaiShouParser as KuaiShouParser
from ..download import YTDLP_DOWNLOADER
from .xiaohongshu import XiaoHongShuParser as XiaoHongShuParser

if YTDLP_DOWNLOADER is not None:
    from .tiktok import TikTokParser as TikTokParser
    from .youtube import YouTubeParser as YouTubeParser

from .base import handle
from .data import (
    Author,
    Platform,
    ParseResult,
    AudioContent,
    ImageContent,
    VideoContent,
    DynamicContent,
    GraphicsContent,
)

__all__ = [
    "AudioContent",
    "Author",
    "BaseParser",
    "DynamicContent",
    "GraphicsContent",
    "ImageContent",
    "ParseResult",
    "Platform",
    "VideoContent",
    "handle",
]
