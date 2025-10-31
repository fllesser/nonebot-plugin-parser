"""统一的解析器 matcher"""

from typing import Literal

from nonebot import get_driver, logger
from nonebot.adapters import Event
from nonebot_plugin_alconna import SupportAdapter

from ..config import pconfig
from ..parsers import BaseParser, ParseResult
from ..renders import get_renderer
from ..utils import LimitedSizeDict
from .rule import Searched, SearchResult, on_keyword_regex


def _get_enabled_parser_classes() -> list[type[BaseParser]]:
    disabled_platforms = set(pconfig.disabled_platforms)
    all_subclass = BaseParser.get_all_subclass()
    return [_cls for _cls in all_subclass if _cls.platform.name not in disabled_platforms]


# 关键词 Parser 映射
KEYWORD_PARSER_MAP: dict[str, BaseParser] = {}


@get_driver().on_startup
def register_parser_matcher():
    enabled_parser_classes = _get_enabled_parser_classes()

    enabled_platform_names = []
    for _cls in enabled_parser_classes:
        parser = _cls()
        enabled_platform_names.append(parser.platform.display_name)
        for keyword, _ in _cls.patterns:
            KEYWORD_PARSER_MAP[keyword] = parser
    logger.info(f"启用平台: {', '.join(sorted(enabled_platform_names))}")

    parser_matcher = on_keyword_regex(*[pattern for _cls in enabled_parser_classes for pattern in _cls.patterns])
    parser_matcher.append_handler(parser_handler)


# 缓存结果
_RESULT_CACHE = LimitedSizeDict[str, ParseResult](max_size=50)


def clear_result_cache():
    _RESULT_CACHE.clear()


async def parser_handler(
    event: Event,
    sr: SearchResult = Searched(),
):
    """统一的解析处理器"""
    # 响应用户处理中
    await _message_reaction(event, "resolving")

    # 1. 获取缓存结果
    cache_key = sr.searched.group(0)
    result = _RESULT_CACHE.get(cache_key)

    if result is None:
        # 2. 获取对应平台 parser
        parser = KEYWORD_PARSER_MAP[sr.keyword]

        try:
            result = await parser.parse(sr.keyword, sr.searched)
        except Exception:
            # await UniMessage(str(e)).send()
            await _message_reaction(event, "fail")
            raise
        logger.debug(f"解析结果: {result}")
    else:
        logger.debug(f"命中缓存: {cache_key}, 结果: {result}")

    # 3. 渲染内容消息并发送
    try:
        renderer = get_renderer(result.platform.name)
        async for message in renderer.render_messages(result):
            await message.send()
    except Exception:
        await _message_reaction(event, "fail")
        raise

    # 4. 无 raise 再缓存解析结果
    _RESULT_CACHE[cache_key] = result

    # 5. 添加成功的消息响应
    await _message_reaction(event, "done")


from nonebot_plugin_alconna import uniseg


async def _message_reaction(
    event: Event,
    status: Literal["fail", "resolving", "done"],
) -> None:
    emoji_map = {
        "fail": ["10060", "❌"],
        "resolving": ["424", "👀"],
        "done": ["144", "🎉"],
    }
    message_id = uniseg.get_message_id(event)
    target = uniseg.get_target(event)
    if target.adapter == SupportAdapter.onebot11:
        emoji = emoji_map[status][0]
    else:
        emoji = emoji_map[status][1]

    await uniseg.message_reaction(emoji, message_id=message_id)
