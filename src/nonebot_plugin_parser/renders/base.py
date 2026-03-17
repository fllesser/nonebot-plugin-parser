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
from ..parsers import ParseResult, AudioContent, ImageContent, VideoContent, DynamicContent
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
        forwardable_segs: list[ForwardNodeInner] = []
        dynamic_segs: list[ForwardNodeInner] = []

        if self.result.video:
            video_path = await self.result.video.path_task.get()
            yield UniMessage(UniHelper.video_seg(video_path))

        for cont in chain(
            self.result.contents,
            self.result.graphics,
            *(self.result.repost.contents, self.result.repost.graphics) if self.result.repost else (),
        ):
            if isinstance(cont, str):
                forwardable_segs.append(cont)
                continue

            try:
                path = await cont.path_task.get()
            except IgnoreException:
                continue
            except DownloadException:
                failed_count += 1
                continue

            match cont:
                case VideoContent():
                    yield UniMessage(UniHelper.video_seg(path))
                case AudioContent():
                    yield UniMessage(UniHelper.record_seg(path))
                case ImageContent():
                    img_seg = UniHelper.img_seg(path)
                    if cont.alt:
                        img_seg += cont.alt
                    forwardable_segs.append(img_seg)
                case DynamicContent():
                    dynamic_segs.append(UniHelper.video_seg(path))

        if self.result.repost and self.result.repost.video:
            video_path = await self.result.repost.video.path_task.get()
            yield UniMessage(UniHelper.video_seg(video_path))

        if forwardable_segs:
            if pconfig.need_forward_contents or len(forwardable_segs) > 4:
                forward_msg = UniHelper.construct_forward_message(forwardable_segs + dynamic_segs)
                yield UniMessage(forward_msg)
            else:
                yield UniMessage(forwardable_segs)

                if dynamic_segs:
                    yield UniMessage(UniHelper.construct_forward_message(dynamic_segs))

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
