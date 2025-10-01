from dataclasses import dataclass, field
from pathlib import Path

from ..constants import ANDROID_HEADER as ANDROID_HEADER
from ..constants import COMMON_HEADER as COMMON_HEADER
from ..constants import IOS_HEADER as IOS_HEADER


@dataclass
class AudioContent:
    """音频内容"""

    audio_path: Path | None = None


@dataclass
class VideoContent:
    """视频内容"""

    video_path: Path | None = None


@dataclass
class ImageContent:
    """图片内容"""

    pic_paths: list[Path] = field(default_factory=list)
    dynamic_paths: list[Path] = field(default_factory=list)


@dataclass
class MultipleContent:
    """多组 图文 内容"""

    text_image_pairs: list[tuple[str, Path | None]] = field(default_factory=list)


@dataclass
class ParseResult:
    """完整的解析结果"""

    title: str
    platform: str  # 平台名称，如 "抖音"、"哔哩哔哩"等
    author: str | None = None
    cover_url: str | None = None
    cover_path: Path | None = None
    content: AudioContent | VideoContent | ImageContent | MultipleContent | None = None
    extra_info: str | None = None  # 额外信息，如视频时长、AI总结等

    @property
    def video_path(self) -> Path | None:
        if isinstance(self.content, VideoContent):
            return self.content.video_path
        return None

    @property
    def pic_paths(self) -> list[Path] | None:
        if isinstance(self.content, ImageContent):
            return self.content.pic_paths
        return None

    @property
    def dynamic_paths(self) -> list[Path] | None:
        if isinstance(self.content, ImageContent):
            return self.content.dynamic_paths
        return None

    @property
    def audio_path(self) -> Path | None:
        if isinstance(self.content, AudioContent):
            return self.content.audio_path
        return None

    def __str__(self) -> str:
        return (
            f"title: {self.title}\nplatform: {self.platform}\nauthor: {self.author}\n"
            f"cover_url: {self.cover_url}\ncover_path: {self.cover_path}\ncontent: {self.content}"
        )
