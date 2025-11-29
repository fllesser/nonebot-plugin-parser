import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar
from pathlib import Path
from itertools import chain
from collections.abc import AsyncGenerator
from typing_extensions import override

from ..config import pconfig
from ..helper import UniHelper, UniMessage, ForwardNodeInner
from ..parsers import (
    ParseResult,
    AudioContent,
    ImageContent,
    VideoContent,
    DynamicContent,
    GraphicsContent,
)
from ..exception import DownloadException, ZeroSizeException, DownloadLimitException


class BaseRenderer(ABC):
    """统一的渲染器，将解析结果转换为消息"""

    templates_dir: ClassVar[Path] = Path(__file__).parent / "templates"
    """模板目录"""

    @abstractmethod
    async def render_messages(self, result: ParseResult) -> AsyncGenerator[UniMessage[Any], None]:
        """消息生成器

        Args:
            result (ParseResult): 解析结果

        Returns:
            AsyncGenerator[UniMessage[Any], None]: 消息生成器
        """
        if False:
            yield
        raise NotImplementedError

    async def render_contents(self, result: ParseResult) -> AsyncGenerator[UniMessage[Any], None]:
        """渲染媒体内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            AsyncGenerator[UniMessage[Any], None]: 消息生成器
        """
        failed_count = 0
        forwardable_segs: list[ForwardNodeInner] = []
        dynamic_segs: list[ForwardNodeInner] = []

        for cont in chain(result.contents, result.repost.contents if result.repost else ()):
            try:
                path = await cont.get_path()
            # 继续渲染其他内容, 类似之前 gather (return_exceptions=True) 的处理
            except (DownloadLimitException, ZeroSizeException):
                # 预期异常，不抛出
                # yield UniMessage(e.message)
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
                    forwardable_segs.append(UniHelper.img_seg(path))
                case DynamicContent():
                    dynamic_segs.append(UniHelper.video_seg(path))
                case GraphicsContent() as graphics:
                    graphics_msg = UniHelper.img_seg(path)
                    if graphics.text is not None:
                        graphics_msg = graphics.text + graphics_msg
                    if graphics.alt is not None:
                        graphics_msg = graphics_msg + graphics.alt
                    forwardable_segs.append(graphics_msg)

        if forwardable_segs:
            if result.text:
                forwardable_segs.append(result.text)

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
    async def render_image(self, result: ParseResult) -> bytes:
        """渲染图片

        Args:
            result (ParseResult): 解析结果

        Returns:
            bytes: 图片字节 png 格式
        """
        raise NotImplementedError

    @override
    async def render_messages(self, result: ParseResult):
        """渲染消息

        Args:
            result (ParseResult): 解析结果
        """
        image_seg = await self.cache_or_render_image(result)

        msg = UniMessage(image_seg)
        if self.append_url:
            urls = (result.display_url, result.repost_display_url)
            msg += "\n".join(url for url in urls if url)
        yield msg

        # 媒体内容
        async for message in self.render_contents(result):
            yield message

    async def cache_or_render_image(self, result: ParseResult):
        """获取缓存图片

        Args:
            result (ParseResult): 解析结果

        Returns:
            Image: 图片 Segment
        """
        if result.render_image is None:
            image_raw = await self.render_image(result)
            image_path = await self.save_img(image_raw)
            result.render_image = image_path
            if pconfig.use_base64:
                return UniHelper.img_seg(raw=image_raw)

        return UniHelper.img_seg(result.render_image)

    @classmethod
    async def save_img(cls, raw: bytes) -> Path:
        """保存图片

        Args:
            raw (bytes): 图片字节

        Returns:
            Path: 图片路径
        """
        import aiofiles

        file_name = f"{uuid.uuid4().hex}.png"
        image_path = pconfig.cache_dir / file_name
        async with aiofiles.open(image_path, "wb+") as f:
            await f.write(raw)
        return image_path
