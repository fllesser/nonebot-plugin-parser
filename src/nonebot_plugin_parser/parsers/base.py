"""Parser 基类定义"""

from abc import ABC, abstractmethod
import re
from typing import ClassVar
from typing_extensions import Unpack

from .data import ParseResult, ParseResultKwargs, Platform


class BaseParser(ABC):
    """所有平台 Parser 的抽象基类

    子类必须实现：
    - platform: 平台信息（包含名称和显示名称）
    - patterns: URL 正则表达式模式列表
    - parse: 解析 URL 的方法（接收正则表达式对象）
    """

    # 类变量：存储所有已注册的 Parser 类
    _registry: ClassVar[list[type["BaseParser"]]] = []

    platform: ClassVar[Platform]
    """ 平台信息（包含名称和显示名称） """

    patterns: ClassVar[list[tuple[str, str]]]
    """ URL 正则表达式模式列表 [(keyword, pattern), ...] """

    def __init_subclass__(cls, **kwargs):
        """自动注册子类到 _registry"""
        super().__init_subclass__(**kwargs)
        if ABC not in cls.__bases__:  # 跳过抽象类
            BaseParser._registry.append(cls)

    @classmethod
    def get_all_subclass(cls) -> list[type["BaseParser"]]:
        """获取所有已注册的 Parser 类"""
        return cls._registry

    @abstractmethod
    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        raise NotImplementedError

    @classmethod
    def result(cls, **kwargs: Unpack[ParseResultKwargs]) -> ParseResult:
        """构建解析结果"""
        return ParseResult(platform=cls.platform, **kwargs)
