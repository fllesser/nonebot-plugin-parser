from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, ClassVar

from ..helper import UniHelper as UniHelper
from ..helper import UniMessage as UniMessage
from ..parsers import ParseResult as ParseResult


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
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            AsyncGenerator[UniMessage[Any], None]: 消息生成器
        """
        separate_segs, forwardable_segs = await result.contents_to_segs()

        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 如果只有 str 类型, 则不使用转发消息
            if all(isinstance(seg, str) for seg in forwardable_segs):
                yield UniMessage(forwardable_segs)
            else:
                forward_msg = UniHelper.construct_forward_message(forwardable_segs)
                yield UniMessage(forward_msg)

        # 处理必须单独发送的消息段
        if separate_segs:
            for seg in separate_segs:
                yield UniMessage(seg)
