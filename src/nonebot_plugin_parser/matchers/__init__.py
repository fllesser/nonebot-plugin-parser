"""统一的解析器 matcher"""

import re
from typing import Literal

from nonebot import get_driver, logger
from nonebot.adapters import Event
from nonebot_plugin_alconna import SupportAdapter
from nonebot_plugin_alconna.uniseg import get_message_id, get_target, message_reaction

from ..config import rconfig
from ..parsers import BaseParser, ParseResult
from ..renders import get_renderer
from ..utils import LimitedSizeDict
from .preprocess import KeyPatternMatched, Keyword, on_keyword_regex


def _get_enabled_parser_classes() -> list[type[BaseParser]]:
    disabled_platforms = set(rconfig.r_disabled_platforms)
    all_subclass = BaseParser.get_all_subclass()
    return [_cls for _cls in all_subclass if _cls.platform.name not in disabled_platforms]


ENABLED_PARSER_CLASSES = _get_enabled_parser_classes()


def _get_enabled_patterns() -> list[tuple[str, str]]:
    """根据配置获取启用的平台正则表达式列表"""

    return [pattern for _cls in ENABLED_PARSER_CLASSES for pattern in _cls.patterns]


# 关键词 Parser 映射
KEYWORD_PARSER_MAP: dict[str, BaseParser] = {}


@get_driver().on_startup
def build_keyword_parsers_map():
    enabled_platform_names = []
    for _cls in ENABLED_PARSER_CLASSES:
        parser = _cls()
        enabled_platform_names.append(parser.platform.display_name)
        for keyword, _ in _cls.patterns:
            KEYWORD_PARSER_MAP[keyword] = parser
    logger.info(f"启动的平台: {', '.join(sorted(enabled_platform_names))}")


# 缓存结果
RESULT_CACHE = LimitedSizeDict[str, ParseResult](max_size=50)

parser_matcher = on_keyword_regex(*_get_enabled_patterns())


@parser_matcher.handle()
async def _(
    event: Event,
    keyword: str = Keyword(),
    matched: re.Match[str] = KeyPatternMatched(),
):
    """统一的解析处理器"""
    # 响应用户处理中
    await _message_reaction(event, "resolving")

    cache_key = matched.group(0)
    if result := RESULT_CACHE.get(cache_key):
        logger.debug(f"命中缓存: {cache_key}")
    else:
        # 获取对应平台 parser
        parser = KEYWORD_PARSER_MAP.get(keyword)

        if parser is None:
            logger.warning("没有找到对应平台的 Parser")
            return

        try:
            result = await parser.parse(matched)
        except Exception:
            # await UniMessage(str(e)).send()
            await _message_reaction(event, "fail")
            raise

        # 缓存解析结果
        RESULT_CACHE[cache_key] = result

    # 3. 渲染内容消息并发送
    renderer = get_renderer(result.platform.name)
    messages = await renderer.render_messages(result)
    for message in messages:
        await message.send()

    # 4. 添加成功的消息响应
    await _message_reaction(event, "done")


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
