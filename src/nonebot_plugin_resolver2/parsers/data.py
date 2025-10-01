from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..constants import ANDROID_HEADER as ANDROID_HEADER
from ..constants import COMMON_HEADER as COMMON_HEADER
from ..constants import IOS_HEADER as IOS_HEADER
from ..matchers.helper import Segment, UniHelper, UniMessage


@dataclass
class AudioContent:
    """音频内容"""

    path: Path


@dataclass
class VideoContent:
    """视频内容"""

    path: Path


@dataclass
class ImageContent:
    """图片内容"""

    path: Path


@dataclass
class DynamicContent:
    """动态内容 视频格式 后续转 gif"""

    path: Path
    gif_path: Path | None = None


@dataclass
class TextImageContent:
    """图文内容"""

    text: str
    image_path: Path


Contents = list[str | AudioContent | VideoContent | ImageContent | TextImageContent]


@dataclass
class ParseResult:
    """完整的解析结果"""

    title: str
    platform: str  # 平台名称，如 "抖音"、"哔哩哔哩"等
    author: str | None = None
    cover_path: Path | None = None
    contents: Contents = field(default_factory=list)
    extra_info: str | None = None  # 额外信息，如视频时长、AI总结等

    @property
    def video_paths(self) -> Sequence[Path]:
        return [cont.path for cont in self.contents if isinstance(cont, VideoContent)]

    @property
    def audio_paths(self) -> Sequence[Path]:
        return [cont.path for cont in self.contents if isinstance(cont, AudioContent)]

    @property
    def img_paths(self) -> Sequence[Path]:
        return [cont.path for cont in self.contents if isinstance(cont, ImageContent)]

    @property
    def dynamic_paths(self) -> Sequence[Path]:
        return [cont.path for cont in self.contents if isinstance(cont, DynamicContent)]

    @property
    def gif_paths(self) -> Sequence[Path]:
        paths = [cont.gif_path for cont in self.contents if isinstance(cont, DynamicContent)]
        return [path for path in paths if path is not None]

    def convert_segs(self):
        separate_segs: list[Segment] = []  # 必须单独发送的消息段(视频、语音、文件)
        forwardable_segs: list[str | Segment | UniMessage] = []  # 可以合并转发的消息段(文本和图片)

        if self.title:
            forwardable_segs.append(f"标题: {self.title}")

        if self.extra_info:
            forwardable_segs.append(self.extra_info)

        if self.cover_path:
            forwardable_segs.append(UniHelper.img_seg(self.cover_path))

        for cont in self.contents:
            if isinstance(cont, str):
                forwardable_segs.append(cont)
            elif isinstance(cont, ImageContent):
                forwardable_segs.append(UniHelper.img_seg(cont.path))
            elif isinstance(cont, DynamicContent):
                forwardable_segs.append(UniHelper.video_seg(cont.path))
            elif isinstance(cont, TextImageContent):
                forwardable_segs.append(cont.text + UniHelper.img_seg(cont.image_path))

            elif isinstance(cont, AudioContent):
                separate_segs.append(UniHelper.record_seg(cont.path))
            elif isinstance(cont, VideoContent):
                separate_segs.append(UniHelper.video_seg(cont.path))

        return separate_segs, forwardable_segs

    def __str__(self) -> str:
        return (
            f"title: {self.title}\nplatform: {self.platform}\nauthor: {self.author}\n"
            f"cover_path: {self.cover_path}\ncontents: {self.contents}"
        )
