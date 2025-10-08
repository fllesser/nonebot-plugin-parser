from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from itertools import chain
from pathlib import Path
from typing import Any, ClassVar
import uuid

from ..config import pconfig
from ..exception import DownloadException, DownloadLimitException, ZeroSizeException
from ..helper import ForwardNodeInner, UniHelper, UniMessage
from ..parsers import ParseResult
from ..parsers.data import AudioContent, DynamicContent, GraphicsContent, ImageContent, VideoContent


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
                    forwardable_segs.append(UniHelper.video_seg(path))
                case GraphicsContent(_, text):
                    forwardable_segs.append(text + UniHelper.img_seg(path))

        if forwardable_segs:
            forward_msg = UniHelper.construct_forward_message(forwardable_segs)
            yield UniMessage(forward_msg)

        if failed_count > 0:
            message = f"{failed_count} 项媒体下载失败"
            yield UniMessage(message)
            raise DownloadException(message)

    @property
    def append_url(self) -> bool:
        return pconfig.append_url

    @property
    def use_base64(self) -> bool:
        return pconfig.use_base64

    async def save_img(self, raw: bytes) -> Path:
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

    async def render_image(self, result: ParseResult) -> bytes:
        """渲染图片

        Args:
            result (ParseResult): 解析结果

        Returns:
            Path: 图片路径
        """
        raise NotImplementedError

    async def cache_or_render_image(self, result: ParseResult) -> Path:
        """获取缓存图片

        Args:
            result (ParseResult): 解析结果

        Returns:
            Path: 图片路径
        """
        if result.render_image is None:
            image_raw = await self.render_image(result)
            image_path = await self.save_img(image_raw)
            result.render_image = image_path
        return result.render_image
