from abc import ABC, abstractmethod

from ..config import NEED_FORWARD
from ..helper import UniMessage
from ..parsers import ParseResult


class BaseRenderer(ABC):
    """统一的渲染器，将解析结果转换为消息"""

    @staticmethod
    @abstractmethod
    async def render_messages(result: ParseResult) -> list[UniMessage]:
        raise NotImplementedError

    @staticmethod
    def need_forward() -> bool:
        return NEED_FORWARD
