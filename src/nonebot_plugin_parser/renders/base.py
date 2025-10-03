from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from ..config import NEED_FORWARD
from ..helper import UniHelper as UniHelper
from ..helper import UniMessage as UniMessage
from ..parsers import ParseResult as ParseResult


class BaseRenderer(ABC):
    """统一的渲染器，将解析结果转换为消息"""

    templates_dir: ClassVar[Path] = Path(__file__).parent / "templates"
    """模板目录"""

    @abstractmethod
    async def render_messages(self, result: ParseResult) -> list[UniMessage]:
        raise NotImplementedError

    @property
    def need_forward(self) -> bool:
        return NEED_FORWARD
