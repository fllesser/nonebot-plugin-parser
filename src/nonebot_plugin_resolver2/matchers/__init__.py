"""统一的解析器 matcher"""

import re
from typing import Literal

from nonebot import logger
from nonebot.adapters import Event
from nonebot_plugin_alconna import SupportAdapter
from nonebot_plugin_alconna.uniseg import get_message_id, get_target, message_reaction

from nonebot_plugin_resolver2.exception import ResolverException

from ..config import rconfig
from ..parsers import PLATFORM_PARSERS, BaseParser, ParseResult
from ..utils import LimitedSizeDict
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


# 缓存结果
RESULT_CACHE = LimitedSizeDict[str, ParseResult](max_size=100)

# 构建关键词到平台的映射（keyword -> platform_name）
KEYWORD_TO_PLATFORM = _build_keyword_to_platform_map(PLATFORM_PARSERS)

# 根据配置创建只包含启用平台的 matcher
resolver = on_keyword_regex(*_get_enabled_patterns(PLATFORM_PARSERS))


async def _message_reaction(event: Event, status: Literal["fail", "resolving", "done"]) -> None:
    emoji_map = {
        "fail": ["10060", "❌"],
        "resolving": ["424", "👀"],
        "done": ["144", "🎉"],
    }
    message_id = get_message_id(event)
    target = get_target(event)
    if target.adapter == SupportAdapter.onebot11:
        emoji = emoji_map[status][0]
    else:
        emoji = emoji_map[status][1]

    await message_reaction(emoji, message_id=message_id)


@resolver.handle()
async def _(
    event: Event,
    keyword: str = Keyword(),
    matched: re.Match[str] = KeyPatternMatched(),
):
    """统一的解析处理器"""
    # 响应用户处理中
    await _message_reaction(event, "resolving")

    key = matched.group(0)
    if result := RESULT_CACHE.get(key):
        logger.debug(f"命中缓存: {key}")
    else:
        # 获取对应平台
        platform = KEYWORD_TO_PLATFORM.get(keyword)
        if not platform:
            logger.warning(f"未找到关键词 {keyword} 对应的平台")
            return
        # 获取对应平台的解析器
        parser_class = PLATFORM_PARSERS.get(platform)
        if not parser_class:
            logger.warning(f"未找到平台 {platform} 的解析器")
            return
        parser = parser_class()

        # 解析
        try:
            result = await parser.parse(matched)
        except ResolverException:
            # await UniMessage(str(e)).send()
            await _message_reaction(event, "fail")
            raise

        # 缓存解析结果
        RESULT_CACHE[key] = result

    # 3. 渲染内容消息并发送
    messages = Renderer.render_messages(result)
    for message in messages:
        await message.send()

    # 4. 添加成功的消息响应
    await _message_reaction(event, "done")
