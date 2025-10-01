"""Parser 基类定义"""

from abc import ABC, abstractmethod
import re
from typing import ClassVar

from .data import ParseResult


class BaseParser(ABC):
    """所有平台 Parser 的抽象基类

    子类必须实现：
    - platform_name: 平台名称（用于配置和内部标识）
    - platform_display_name: 平台显示名称（用于展示）
    - patterns: URL 正则表达式模式列表
    - parse: 解析 URL 的方法（接收正则表达式对象）
    """

    platform_name: ClassVar[str]
    """ 平台名称（用于配置和内部标识） """

    platform_display_name: ClassVar[str]
    """ 平台显示名称（用于展示） """

    patterns: ClassVar[list[tuple[str, str]]]
    """ URL 正则表达式模式列表 [(keyword, pattern), ...] """

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
