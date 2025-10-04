from asyncio import Task
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any

from ..constants import ANDROID_HEADER as ANDROID_HEADER
from ..constants import COMMON_HEADER as COMMON_HEADER
from ..constants import IOS_HEADER as IOS_HEADER
from ..exception import ParseException
from ..helper import Segment, UniHelper, UniMessage


@dataclass
class MediaContent:
    pass


@dataclass
class AudioContent(MediaContent):
    """音频内容"""

    path: Path
    duration: float = 0.0


@dataclass
class VideoContent(MediaContent):
    """视频内容"""

    path_or_task: Path | Task[Path]
    """视频路径"""
    cover_path: Path | None = None
    """视频封面"""
    duration: float = 0.0
    """时长 单位: 秒"""

    async def video_path(self) -> Path:
        if isinstance(self.path_or_task, Path):
            return self.path_or_task
        if isinstance(self.path_or_task, Task):
            self.path_or_task = await self.path_or_task
            return self.path_or_task
        raise ValueError("视频路径或下载任务为空")

    @property
    def display_duration(self) -> str:
        minutes = int(self.duration) // 60
        seconds = int(self.duration) % 60
        return f"时长: {minutes}:{seconds:02d}"


@dataclass
class ImageContent(MediaContent):
    """图片内容"""

    path: Path


@dataclass
class DynamicContent(MediaContent):
    """动态内容 视频格式 后续转 gif"""

    path: Path
    gif_path: Path | None = None


@dataclass
class TextImageContent:
    """图文内容"""

    text: str
    image_path: Path


Content = str | MediaContent | TextImageContent


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
    title: str = ""
    """标题"""
    text: str = ""
    """文本内容"""
    cover_path: Path | None = None
    """封面"""
    contents: list[Content] = field(default_factory=list)
    """内容列表，主体以外的内容"""
    timestamp: float | None = None
    """发布时间戳, 秒"""
    url: str | None = None
    """来源链接"""
    author: Author | None = None
    """作者信息"""
    extra: dict[str, Any] = field(default_factory=dict)
    """额外信息"""
    repost: "ParseResult | None" = None
    """转发的内容"""

    @property
    def header(self) -> str:
        header = self.platform.display_name
        if self.author:
            header += f" @{self.author.name}"
        if self.title:
            header += f" | {self.title}"
        return header

    @property
    def video_contents(self) -> Sequence[VideoContent]:
        return [cont for cont in self.contents if isinstance(cont, VideoContent)]

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

    @property
    def display_url(self) -> str:
        return f"链接: {self.url}" if self.url else ""

    @property
    def repost_display_url(self) -> str:
        return f"原帖: {self.repost.url}" if self.repost and self.repost.url else ""

    @property
    def extra_info(self) -> str:
        return self.extra.get("info", "")

    def formart_datetime(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return datetime.fromtimestamp(self.timestamp).strftime(fmt) if self.timestamp else ""

    async def contents_to_segs(self):
        """将内容列表转换为消息段

        Returns:
            tuple[list[Segment], list[str | Segment | UniMessage]]: 消息段
            separate_segs: 必须单独发送的消息段(视频、语音、文件)
            forwardable_segs: 可以合并转发的消息段(文本和图片)
        """
        separate_segs: list[Segment] = []
        forwardable_segs: list[str | Segment | UniMessage] = []

        for cont in chain(self.contents, self.repost.contents if self.repost else ()):
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
                case VideoContent() as video:
                    try:
                        video_path = await video.video_path()
                        separate_segs.append(UniHelper.video_seg(video_path))
                    except ParseException as e:
                        forwardable_segs.append(e.message)

        return separate_segs, forwardable_segs

    def __str__(self) -> str:
        return f"title: {self.title}\nplatform: {self.platform}\nauthor: {self.author}\ncontents: {self.contents}"


from dataclasses import dataclass, field
from typing import Any, TypedDict


class ParseResultKwargs(TypedDict, total=False):
    title: str
    text: str
    cover_path: Path | None
    contents: list[Content]
    timestamp: float | None
    url: str | None
    author: Author | None
    extra: dict[str, Any]
    repost: ParseResult | None
