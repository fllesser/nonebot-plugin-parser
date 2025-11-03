# 导出所有 Parser 类
from .acfun import AcfunParser as AcfunParser  # noqa: I001
from .base import BaseParser as BaseParser
from .data import ParseResult as ParseResult
from .douyin import DouyinParser as DouyinParser
from .kuaishou import KuaiShouParser as KuaiShouParser
from .nga import NGAParser as NGAParser
from .twitter import TwitterParser as TwitterParser
from .weibo import WeiBoParser as WeiBoParser
from .xiaohongshu import XiaoHongShuParser as XiaoHongShuParser

from .bilibili import BilibiliParser as BilibiliParser

try:
    import yt_dlp as yt_dlp

    from .tiktok import TikTokParser as TikTokParser
    from .youtube import YouTubeParser as YouTubeParser
except ImportError:
    pass

__all__ = [
    "ParseResult",
]
