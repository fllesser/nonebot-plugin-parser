# 导出所有 Parser 类
from .acfun import AcfunParser as AcfunParser
from .base import BaseParser as BaseParser
from .bilibili import BilibiliParser as BilibiliParser
from .data import ParseResult as ParseResult
from .douyin import DouyinParser as DouyinParser
from .kuaishou import KuaishouParser as KuaishouParser
from .tiktok import TikTokParser as TikTokParser
from .twitter import TwitterParser as TwitterParser
from .weibo import WeiBoParser as WeiBoParser
from .xiaohongshu import XiaoHongShuParser as XiaoHongShuParser
from .youtube import YouTubeParser as YouTubeParser

# 自动获取所有已注册的 Parser 类
PARSER_CLASSES: list[type[BaseParser]] = BaseParser.get_all_parsers()

# 自动构建平台映射（platform_name -> Parser 类）
PLATFORM_PARSERS: dict[str, type[BaseParser]] = {
    parser_class.platform_name: parser_class for parser_class in PARSER_CLASSES
}

__all__ = [
    "PARSER_CLASSES",
    "PLATFORM_PARSERS",
    "ParseResult",
]
