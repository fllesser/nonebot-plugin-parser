from abc import ABC, abstractmethod

from nonebot_plugin_alconna import UniMessage

from nonebot_plugin_resolver2.parsers import ParseResult


class BaseRenderer(ABC):
    """统一的渲染器，将解析结果转换为消息"""

    @staticmethod
    @abstractmethod
    async def render_messages(result: ParseResult) -> list[UniMessage]:
        raise NotImplementedError
