import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar
from pathlib import Path
from itertools import chain
from collections.abc import AsyncGenerator
from typing_extensions import override

import aiofiles

from ..config import pconfig
from ..helper import UniHelper, UniMessage, ForwardNodeInner
from ..parsers import ParseResult, AudioContent, ImageContent, VideoContent
from ..exception import IgnoreException, DownloadException


class BaseRenderer(ABC):
    """统一的渲染器，将解析结果转换为消息"""

    templates_dir: ClassVar[Path] = Path(__file__).parent / "templates"
    """模板目录"""

    def __init__(self, result: ParseResult, not_repost: bool = True) -> None:
        self.result = result
        self.not_repost = not_repost

    @abstractmethod
    async def render_messages(self) -> AsyncGenerator[UniMessage[Any], None]:
        """渲染解析结果"""
        if False:
            yield
        raise NotImplementedError

    async def render_contents(self) -> AsyncGenerator[UniMessage[Any], None]:
        failed_count = 0
        # 可合并的 Seg，例如 文字，图片
        mergeable_segs: list[ForwardNodeInner] = []
        # 不可合并的 Seg，例如 视频，语音
        other_segs: list[ForwardNodeInner] = []

        def on_error(e: Exception):
            if isinstance(e, IgnoreException):
                pass
            elif isinstance(e, DownloadException):
                nonlocal failed_count
                failed_count += 1

        for cont in chain(
            self.result.contents,
            self.result.repost.contents if self.result.repost else (),
        ):
            path = await cont.path_task.safe_get(on_error)
            if path is None:
                continue

            match cont:
                case VideoContent() as video:
                    if video.gif_path and (gif_path := await video.gif_path.safe_get()):
                        mergeable_segs.append(UniHelper.img_seg(gif_path))
                    else:
                        thumbnail = await video.cover.safe_get() if video.cover else None
                        yield UniMessage(UniHelper.video_seg(path, thumbnail))
                case AudioContent():
                    yield UniMessage(UniHelper.record_seg(path))
                case ImageContent():
                    mergeable_segs.append(UniHelper.img_seg(path))

        for cont in chain(
            self.result.graphics,
            self.result.repost.graphics if self.result.repost else (),
        ):
            if isinstance(cont, str):
                mergeable_segs.append(cont)
                continue

            if path := await cont.path_task.safe_get(on_error):
                img_seg = UniHelper.img_seg(path)
                if cont.alt:
                    img_seg += cont.alt
                mergeable_segs.append(img_seg)

        if mergeable_segs or other_segs:
            if pconfig.need_forward_contents or len(other_segs) > 1 or (len(mergeable_segs) + len(other_segs)) > 4:
                forward_msg = UniHelper.construct_forward_message(mergeable_segs + other_segs)
                yield UniMessage(forward_msg)
            else:
                if mergeable_segs:
                    yield UniMessage(mergeable_segs)
                for other_seg in other_segs:
                    yield UniMessage(other_seg)

        if failed_count > 0:
            message = f"{failed_count} 项媒体下载失败"
            yield UniMessage(message)
            raise DownloadException(message)

    @property
    def append_url(self) -> bool:
        return pconfig.append_url


class ImageRenderer(BaseRenderer):
    """图片渲染器"""

    @abstractmethod
    async def render_image(self) -> bytes:
        """渲染图片"""
        raise NotImplementedError

    @override
    async def render_messages(self):
        image_seg = await self.cache_or_render_image()

        msg = UniMessage(image_seg)
        if self.append_url:
            urls = (self.result.display_url, self.result.repost_display_url)
            msg += "\n".join(url for url in urls if url)
        yield msg

        # 媒体内容
        async for message in self.render_contents():
            yield message

    async def cache_or_render_image(self):
        """获取缓存图片"""
        if self.result.render_image is None:
            image_raw = await self.render_image()
            image_path = await self.save_img(image_raw)
            self.result.render_image = image_path
            if pconfig.use_base64:
                return UniHelper.img_seg(image_raw)

        return UniHelper.img_seg(self.result.render_image)

    @classmethod
    async def save_img(cls, raw: bytes) -> Path:
        """保存图片"""
        file_name = f"{uuid.uuid4().hex}.png"
        image_path = pconfig.cache_dir / file_name
        async with aiofiles.open(image_path, "wb+") as f:
            await f.write(raw)
        return image_path
