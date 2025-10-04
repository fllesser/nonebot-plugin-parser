from asyncio import Task
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
    path_task: Path | Task[Path]

    async def get_path(self) -> Path:
        if isinstance(self.path_task, Path):
            return self.path_task
        return await self.path_task


@dataclass
class AudioContent(MediaContent):
    """音频内容"""

    duration: float = 0.0


@dataclass
class VideoContent(MediaContent):
    """视频内容"""

    cover: Task[Path] | None = None
    """视频封面"""
    duration: float = 0.0
    """时长 单位: 秒"""

    async def get_cover_path(self) -> Path | None:
        return await self.cover if self.cover else None

    @property
    def display_duration(self) -> str:
        minutes = int(self.duration) // 60
        seconds = int(self.duration) % 60
        return f"时长: {minutes}:{seconds:02d}"


@dataclass
class ImageContent(MediaContent):
    """图片内容"""

    pass


@dataclass
class DynamicContent(MediaContent):
    """动态内容 视频格式 后续转 gif"""

    gif_path: Path | None = None


@dataclass
class GraphicsContent(MediaContent):
    """图文内容"""

    text: str


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
    avatar: Task[Path] | None = None
    """作者头像 URL 或本地路径"""
    description: str | None = None
    """作者个性签名等"""

    @property
    async def avatar_path(self) -> Path | None:
        return await self.avatar if self.avatar else None


@dataclass
class ParseResult:
    """完整的解析结果"""

    platform: Platform
    """平台信息"""
    title: str = ""
    """标题"""
    text: str = ""
    """文本内容"""
    contents: list[MediaContent] = field(default_factory=list)
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

    def __hash__(self) -> int:
        return hash(
            (
                self.platform.name,
                self.timestamp,
                self.url,
            )
        )

    @property
    def header(self) -> str:
        header = self.platform.display_name
        if self.author:
            header += f" @{self.author.name}"
        if self.title:
            header += f" | {self.title}"
        return header

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

    @property
    async def cover_path(self) -> Path | None:
        for cont in self.contents:
            if isinstance(cont, VideoContent):
                return await cont.get_cover_path()
            if isinstance(cont, ImageContent):
                return await cont.get_path()
        return None

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
            try:
                match cont:
                    case VideoContent():
                        separate_segs.append(UniHelper.video_seg(await cont.get_path()))
                    case ImageContent():
                        forwardable_segs.append(UniHelper.img_seg(await cont.get_path()))
                    case AudioContent():
                        separate_segs.append(UniHelper.record_seg(await cont.get_path()))
                    case DynamicContent():
                        forwardable_segs.append(UniHelper.video_seg(await cont.get_path()))
                    case GraphicsContent(_, text):
                        forwardable_segs.append(text + UniHelper.img_seg(await cont.get_path()))
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
    contents: list[MediaContent]
    timestamp: float | None
    url: str | None
    author: Author | None
    extra: dict[str, Any]
    repost: ParseResult | None
