from dataclasses import dataclass, field

from ..constant import ANDROID_HEADER as ANDROID_HEADER
from ..constant import COMMON_HEADER as COMMON_HEADER
from ..constant import IOS_HEADER as IOS_HEADER


@dataclass
class ParseResult:
    """解析结果"""

    # 标题
    title: str

    # 作者
    author: str = ""

    # 封面地址
    cover_url: str = ""

    # 视频地址
    video_url: str = ""

    # 音频地址
    audio_url: str = ""

    # 图片地址
    pic_urls: list[str] = field(default_factory=list)

    # 动态视频地址
    dynamic_urls: list[str] = field(default_factory=list)
