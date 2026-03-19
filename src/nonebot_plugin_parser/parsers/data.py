from __future__ import annotations

import asyncio
from typing import Any, TypedDict
from pathlib import Path
from datetime import datetime
from dataclasses import field, dataclass
from collections.abc import Iterator, Awaitable

from .task import PathTask
from .utils import fmt_duration


@dataclass(repr=False, slots=True)
class MediaContent:
    path_task: PathTask

    async def get_path(self) -> Path:
        return await self.path_task.get()

    def __repr__(self) -> str:
        prefix = self.__class__.__name__
        return f"{prefix}({self.path_task})"


@dataclass(repr=False, slots=True)
class AudioContent(MediaContent):
    """音频内容"""

    duration: float | None = None
    """时长 单位: 秒"""


@dataclass(repr=False, slots=True)
class VideoContent(MediaContent):
    """视频内容"""

    cover: PathTask | None = None
    """视频封面"""
    duration: float | None = None
    """时长 单位: 秒"""
    gif_path: Path | None = None
    """视频转 GIF """

    @property
    def display_duration(self) -> str | None:
        return f"时长: {fmt_duration(self.duration)}" if self.duration else None

    def __repr__(self) -> str:
        repr = f"VideoContent({self.path_task}"
        if self.cover is not None:
            repr += f", cover={self.cover}"
        return repr + ")"


@dataclass(repr=False, slots=True)
class ImageContent(MediaContent):
    """图片内容"""

    alt: str | None = None
    """图片描述 用于图文"""


@dataclass(slots=True)
class Platform:
    """平台信息"""

    name: str
    """ 平台名称 """
    display_name: str
    """ 平台显示名称 """


@dataclass(repr=False, slots=True)
class Author:
    """作者信息"""

    name: str
    """作者名称"""
    avatar: PathTask | None = None
    """作者头像 URL 或本地路径"""
    description: str | None = None
    """作者个性签名等"""

    def __repr__(self) -> str:
        repr = f"Author(name={self.name}"
        if self.avatar:
            repr += f", avatar={self.avatar}"
        if self.description:
            repr += f", description={self.description}"
        return repr + ")"


@dataclass(repr=False, slots=True)
class ParseResult:
    """完整的解析结果"""

    platform: Platform
    """平台信息"""
    author: Author | None = None
    """作者信息"""
    title: str | None = None
    """标题"""
    text: str | None = None
    """文本内容"""
    timestamp: int | None = None
    """发布时间戳, 秒"""
    url: str | None = None
    """来源链接"""

    video: VideoContent | None = None
    """视频内容"""
    contents: list[MediaContent] = field(default_factory=list)
    """其他媒体内容"""
    graphics: list[str | ImageContent] = field(default_factory=list)
    """图文内容"""

    extra: dict[str, Any] = field(default_factory=dict)
    """额外信息"""
    repost: ParseResult | None = None
    """转发的内容"""
    render_image: Path | None = None
    """渲染图片"""

    @property
    def header(self) -> str | None:
        """头信息 仅用于 default render"""
        header = self.platform.display_name
        if self.author:
            header += f" @{self.author.name}"
        if self.title:
            header += f" | {self.title}"
        return header

    @property
    def display_url(self) -> str | None:
        return f"链接: {self.url}" if self.url else None

    @property
    def repost_display_url(self) -> str | None:
        return f"原帖: {self.repost.url}" if self.repost and self.repost.url else None

    @property
    def extra_info(self) -> str | None:
        return self.extra.get("info")

    @property
    def video_contents(self) -> list[VideoContent]:
        """获取视频内容（如果有）"""
        return [cont for cont in self.contents if isinstance(cont, VideoContent)]

    @property
    def img_contents(self) -> list[ImageContent]:
        return [cont for cont in self.contents if isinstance(cont, ImageContent)]

    @property
    def audio_contents(self) -> list[AudioContent]:
        return [cont for cont in self.contents if isinstance(cont, AudioContent)]

    @property
    def all_grid_images(self):
        """获取所有用于渲染图片网格的图片（视频封面 + 图片）"""
        covers: list[PathTask] = []
        for cont in self.contents:
            if isinstance(cont, VideoContent):
                if cont.cover is not None:
                    covers.append(cont.cover)
            elif isinstance(cont, ImageContent):
                covers.append(cont.path_task)
        return covers

    @property
    def formartted_datetime(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> str | None:
        """格式化时间戳"""
        return datetime.fromtimestamp(self.timestamp).strftime(fmt) if self.timestamp is not None else None

    def _iterate_download_coros(
        self,
        img_only: bool = False,
    ) -> Iterator[Awaitable[Path | None]]:
        if author := self.author:
            if author.avatar:
                yield author.avatar.get()

        if self.video:
            if self.video.cover:
                yield self.video.cover.get()
            yield self.video.path_task.get()

        for cont in self.contents:
            if not img_only or isinstance(cont, ImageContent):
                yield cont.path_task.get()

            if isinstance(cont, VideoContent) and cont.cover:
                yield cont.cover.get()

        for gra in self.graphics:
            if isinstance(gra, ImageContent):
                yield gra.path_task.get()

        if self.repost is not None:
            yield from self.repost._iterate_download_coros(img_only)

    async def ensure_downloads_complete(
        self,
        *,
        img_only: bool = False,
        suppress_errors: bool = True,
    ) -> None:
        await asyncio.gather(
            *self._iterate_download_coros(img_only),
            return_exceptions=suppress_errors,
        )

    @property
    def content_type(self) -> str:
        """获取内容类型 (允许解析器通过 extra 显式指定)"""
        content_type = self.extra.get("content_type")

        if content_type is None:
            if self.video:
                return "视频"
            elif self.graphics:
                return "图文"
            else:
                return "动态"
        return content_type

    def __repr__(self) -> str:
        return (
            f"platform: {self.platform.display_name}, "
            f"timestamp: {self.timestamp}, "
            f"title: {self.title}, "
            f"text: {self.text}, "
            f"url: {self.url}, "
            f"author: {self.author}, "
            f"video: {self.video}, "
            f"contents: {self.contents}, "
            f"graphics: {self.graphics}, "
            f"extra: {self.extra}, "
            f"repost: <<<<<<<{self.repost}>>>>>>, "
            f"render_image: {self.render_image.name if self.render_image else 'None'}"
        )


class ParseResultKwargs(TypedDict, total=False):
    title: str | None
    text: str | None
    video: VideoContent | None
    contents: list[MediaContent]
    graphics: list[str | ImageContent]
    timestamp: int | None
    url: str | None
    author: Author | None
    extra: dict[str, Any]
    repost: ParseResult | None
