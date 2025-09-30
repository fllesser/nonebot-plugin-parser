from .acfun import AcfunParser as AcfunParser
from .base import BaseParser as BaseParser
from .bilibili import BilibiliParser as BilibiliParser
from .douyin import DouyinParser as DouyinParser
from .kuaishou import KuaishouParser as KuaishouParser
from .twitter import TwitterParser as TwitterParser
from .utils import get_redirect_url as get_redirect_url
from .weibo import WeiBoParser as WeiBoParser
from .xiaohongshu import XiaoHongShuParser as XiaoHongShuParser

# 注册所有支持的 Parser 类（添加新平台只需在这里添加一行）
PARSER_CLASSES: list[type[BaseParser]] = [
    AcfunParser,
    BilibiliParser,
    DouyinParser,
    KuaishouParser,
    XiaoHongShuParser,
    WeiBoParser,
    TwitterParser,
]

# 自动构建平台映射（platform_name -> Parser 类）
PLATFORM_PARSERS: dict[str, type[BaseParser]] = {
    parser_class.platform_name: parser_class for parser_class in PARSER_CLASSES
}

__all__ = [
    "PARSER_CLASSES",
    "PLATFORM_PARSERS",
    "get_redirect_url",
]
