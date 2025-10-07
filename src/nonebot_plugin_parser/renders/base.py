from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from itertools import chain
from pathlib import Path
from typing import Any, ClassVar

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
