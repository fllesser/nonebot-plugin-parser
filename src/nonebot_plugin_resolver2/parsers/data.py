from dataclasses import dataclass, field

from ..constants import ANDROID_HEADER as ANDROID_HEADER
from ..constants import COMMON_HEADER as COMMON_HEADER
from ..constants import IOS_HEADER as IOS_HEADER


@dataclass
class AudioContent:
    """音频内容"""

    audio_url: str


@dataclass
class VideoContent:
    """视频内容"""

    video_url: str


@dataclass
class ImageContent:
    """图片内容"""

    pic_urls: list[str] = field(default_factory=list)
    dynamic_urls: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """完整的解析结果"""

    title: str
    author: str | None = None
    cover_url: str | None = None
    content: AudioContent | VideoContent | ImageContent | None = None

    @property
    def video_url(self) -> str | None:
        return self.content.video_url if isinstance(self.content, VideoContent) else None

    @property
    def pic_urls(self) -> list[str] | None:
        return self.content.pic_urls if isinstance(self.content, ImageContent) else None

    @property
    def dynamic_urls(self) -> list[str] | None:
        return self.content.dynamic_urls if isinstance(self.content, ImageContent) else None

    @property
    def audio_url(self) -> str | None:
        return self.content.audio_url if isinstance(self.content, AudioContent) else None

    def __str__(self) -> str:
        return f"title: {self.title}\nauthor: {self.author}\ncover_url: {self.cover_url}\ncontent: {self.content}"
