"""统一的解析器 matcher"""

import re

from nonebot import logger

from ..config import rconfig
from ..exception import handle_exception
from ..parsers import PLATFORM_PARSERS
from ..parsers.base import BaseParser
from .preprocess import KeyPatternMatched, Keyword, on_keyword_regex
from .render import Renderer


def _build_keyword_to_platform_map(platform_parsers: dict[str, type[BaseParser]]) -> dict[str, str]:
    """构建关键词到平台名称的映射表"""
    keyword_map = {}
    for platform_name, parser_class in platform_parsers.items():
        for keyword, _ in parser_class.patterns:
            keyword_map[keyword] = platform_name
    return keyword_map


def _get_enabled_patterns(platform_parsers: dict[str, type[BaseParser]]) -> list[tuple[str, str]]:
    """根据配置获取启用的平台正则表达式列表"""
    # 获取禁用的平台列表
    disabled_platforms = set(rconfig.r_disable_resolvers)

    # 如果未配置小红书 cookie，也禁用小红书
    if not rconfig.r_xhs_ck:
        disabled_platforms.add("xiaohongshu")
        logger.warning("未配置小红书 cookie, 小红书解析已关闭")

    # 从各个 Parser 类中收集启用平台的正则表达式
    enabled_patterns: list[tuple[str, str]] = []
    enabled_platform_names: set[str] = set()

    for platform_name, parser_class in platform_parsers.items():
        if platform_name not in disabled_platforms:
            enabled_patterns.extend(parser_class.patterns)
            enabled_platform_names.add(platform_name)

    if enabled_platform_names:
        logger.info(f"启用的平台: {', '.join(sorted(enabled_platform_names))}")

    return enabled_patterns


# 构建关键词到平台的映射（keyword -> platform_name）
KEYWORD_TO_PLATFORM = _build_keyword_to_platform_map(PLATFORM_PARSERS)


# 根据配置创建只包含启用平台的 matcher
resolver = on_keyword_regex(*_get_enabled_patterns(PLATFORM_PARSERS))


@resolver.handle()
@handle_exception()
async def _(
    keyword: str = Keyword(),
    searched: re.Match[str] = KeyPatternMatched(),
):
    """统一的解析处理器"""
    url = searched.group(0)
    platform = KEYWORD_TO_PLATFORM.get(keyword)
    if not platform:
        logger.warning(f"未找到关键词 {keyword} 对应的平台")
        return

    # 获取对应平台的解析器
    parser_class = PLATFORM_PARSERS.get(platform)
    if not parser_class:
        logger.warning(f"未找到平台 {platform} 的解析器")
        return

    # 创建解析器
    parser = parser_class()

    # 1. 先发送初始消息（快速反馈给用户）
    await resolver.send(f"解析 | {parser.platform_display_name}")

    # 2. 解析 URL（包含下载资源）
    result = await parser.parse_url(url)

    if result:
        # 3. 渲染内容消息并发送
        messages = Renderer.render_messages(result)
        for message in messages:
            await message.send()
