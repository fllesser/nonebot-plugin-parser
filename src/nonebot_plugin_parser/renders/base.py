from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from itertools import chain
from pathlib import Path
from typing import Any, ClassVar

from ..exception import ParseException
from ..helper import Segment, UniHelper, UniMessage
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
        forwardable_segs: list[str | Segment | UniMessage] = []
        for cont in chain(result.contents, result.repost.contents if result.repost else ()):
            try:
                path = await cont.get_path()
            except ParseException as e:
                yield UniMessage(e.message)
                raise

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
            if all(isinstance(seg, str) for seg in forwardable_segs):
                yield UniMessage(forwardable_segs)
            else:
                forward_msg = UniHelper.construct_forward_message(forwardable_segs)
                yield UniMessage(forward_msg)
