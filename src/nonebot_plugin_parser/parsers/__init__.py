# 导出所有 Parser 类
from ..download import YTDLP_DOWNLOADER
from .acfun import AcfunParser as AcfunParser
from .base import BaseParser as BaseParser
from .bilibili import BilibiliParser as BilibiliParser
from .douyin import DouyinParser as DouyinParser
from .kuaishou import KuaiShouParser as KuaiShouParser
from .nga import NGAParser as NGAParser
from .twitter import TwitterParser as TwitterParser
from .weibo import WeiBoParser as WeiBoParser
from .xiaohongshu import XiaoHongShuParser as XiaoHongShuParser

if YTDLP_DOWNLOADER is not None:
    from .tiktok import TikTokParser as TikTokParser
    from .youtube import YouTubeParser as YouTubeParser

from .base import handle as handle
from .data import AudioContent as AudioContent
from .data import Author
from .data import DynamicContent as DynamicContent
from .data import GraphicsContent as GraphicsContent
from .data import ImageContent as ImageContent
from .data import ParseResult as ParseResult
from .data import Platform as Platform
from .data import VideoContent as VideoContent

__all__ = [
    "AudioContent",
    "Author",
    "DynamicContent",
    "GraphicsContent",
    "ImageContent",
    "ParseResult",
    "Platform",
    "VideoContent",
    "handle",
]
