from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


Content = str | AudioContent | VideoContent | ImageContent | DynamicContent | TextImageContent


@dataclass
class Platform:
    """平台信息"""

    name: str
    """ 平台名称 """
    display_name: str
    """ 平台显示名称 """


@dataclass
class Author:
    """作者信息"""

    name: str
    """作者名称"""
    avatar: str | Path | None = None
    """作者头像 URL 或本地路径"""
    description: str | None = None
    """作者个性签名等"""


@dataclass
class ParseResult:
    """完整的解析结果"""

    platform: Platform
    """平台信息"""
    content: str
    """文本内容"""
    title: str | None = None
    """标题"""
    contents: list[Content] = field(default_factory=list)
    """内容列表，主体以外的内容"""
    timestamp: float | None = None
    """发布/获取时间戳, 秒"""
    url: str | None = None
    """来源链接"""
    author: Author | None = None
    """作者信息"""
    extra: dict[str, Any] = field(default_factory=dict)
    """额外信息"""
    repost: "ParseResult | None" = None
    """转发的内容"""

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
        """转换为消息段

        Returns:
            tuple[list[Segment], list[str | Segment | UniMessage]]: 消息段
            separate_segs: 必须单独发送的消息段(视频、语音、文件)
            forwardable_segs: 可以合并转发的消息段(文本和图片)
        """
        separate_segs: list[Segment] = []
        forwardable_segs: list[str | Segment | UniMessage] = []

        for cont in self.contents:
            match cont:
                case str():
                    forwardable_segs.append(cont)
                case ImageContent(path):
                    forwardable_segs.append(UniHelper.img_seg(path))
                case DynamicContent(path):
                    # gif_path
                    forwardable_segs.append(UniHelper.video_seg(path))
                case TextImageContent(text, image_path):
                    forwardable_segs.append(text + UniHelper.img_seg(image_path))
                case AudioContent(path):
                    separate_segs.append(UniHelper.record_seg(path))
                case VideoContent(path):
                    separate_segs.append(UniHelper.video_seg(path))

        return separate_segs, forwardable_segs

    def __str__(self) -> str:
        return f"title: {self.title}\nplatform: {self.platform}\nauthor: {self.author}\ncontents: {self.contents}"
