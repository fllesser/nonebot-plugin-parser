from enum import Enum, IntEnum
from typing import Final

from httpx import Timeout

COMMON_HEADER: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/55.0.2883.87 UBrowser/6.2.4098.3 Safari/537.36"
    )
}

IOS_HEADER: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.6 Mobile/15E148 Safari/604.1 Edg/132.0.0.0"
    )
}

ANDROID_HEADER: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 15; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Mobile Safari/537.36 Edg/132.0.0.0"
    )
}

COMMON_TIMEOUT: Final[Timeout] = Timeout(connect=15.0, read=20.0, write=10.0, pool=10.0)

DOWNLOAD_TIMEOUT: Final[Timeout] = Timeout(connect=15.0, read=240.0, write=10.0, pool=10.0)


class BiliVideoCodec(str, Enum):
    """B站视频编码"""

    AVC = "avc"
    AV1 = "av1"
    HEV = "hev"


class BiliVideoQuality(IntEnum):
    """B站视频分辨率"""

    _360P = 16
    _480P = 32
    _720P = 64
    _1080P = 80
    _1080P_PLUS = 112
    _1080P_60 = 116
    _4K = 120


class PlatformEnum(str, Enum):
    ACFUN = "acfun"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    NGA = "nga"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    WEIBO = "weibo"
    XIAOHONGSHU = "xiaohongshu"
    YOUTUBE = "youtube"

    def __str__(self) -> str:
        return self.value


class RenderType(str, Enum):
    default = "default"
    common = "common"
    htmlkit = "htmlkit"
    htmlrender = "htmlrender"
