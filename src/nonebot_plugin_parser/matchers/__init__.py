"""统一的解析器 matcher"""

from nonebot import get_driver, logger

from ..config import pconfig
from ..helper import UniHelper
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
    enabled_classes = _get_enabled_parser_classes()

    enabled_platforms = []
    for _cls in enabled_classes:
        parser = _cls()
        enabled_platforms.append(parser.platform.display_name)
        for keyword, _ in _cls._key_patterns:
            KEYWORD_PARSER_MAP[keyword] = parser
    logger.info(f"启用平台: {', '.join(sorted(enabled_platforms))}")

    patterns = [p for _cls in enabled_classes for p in _cls._key_patterns]
    matcher = on_keyword_regex(*patterns)
    matcher.append_handler(parser_handler)


# 缓存结果
_RESULT_CACHE = LimitedSizeDict[str, ParseResult](max_size=50)


def clear_result_cache():
    _RESULT_CACHE.clear()


@UniHelper.exception_handler
async def parser_handler(
    sr: SearchResult = Searched(),
):
    """统一的解析处理器"""
    # 1. 获取缓存结果
    cache_key = sr.searched.group(0)
    result = _RESULT_CACHE.get(cache_key)

    if result is None:
        # 2. 获取对应平台 parser
        parser = KEYWORD_PARSER_MAP[sr.keyword]
        result = await parser.parse(sr.keyword, sr.searched)
        logger.debug(f"解析结果: {result}")
    else:
        logger.debug(f"命中缓存: {cache_key}, 结果: {result}")

    # 3. 渲染内容消息并发送
    renderer = get_renderer(result.platform.name)
    async for message in renderer.render_messages(result):
        await message.send()

    # 4. 无 raise 再缓存解析结果
    _RESULT_CACHE[cache_key] = result


import re
from typing import cast

from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot_plugin_alconna import UniMessage

from ..download import DOWNLOADER
from ..parsers import BilibiliParser


@on_command("bm", priority=3, block=True).handle()
@UniHelper.exception_handler
async def _(message: Message = CommandArg()):
    text = message.extract_plain_text()
    matched = re.search(r"(BV[A-Za-z0-9]{10})(\s\d{1,3})?", text)
    if not matched:
        await UniMessage("请发送正确的 BV 号").finish()

    bvid, page_num = matched.group(1), matched.group(2)
    page_idx = int(page_num) if page_num else 0

    parser = KEYWORD_PARSER_MAP["BV"]
    parser = cast(BilibiliParser, parser)

    _, audio_url = await parser.extract_download_urls(bvid=bvid, page_index=page_idx)
    if not audio_url:
        await UniMessage("未找到可下载的音频").finish()

    audio_path = await DOWNLOADER.download_audio(
        audio_url, audio_name=f"{bvid}-{page_idx}.mp3", ext_headers=parser.headers
    )
    await UniMessage(UniHelper.record_seg(audio_path)).send()

    if pconfig.need_upload:
        await UniMessage(UniHelper.file_seg(audio_path)).send()


from ..download import YTDLP_DOWNLOADER

if YTDLP_DOWNLOADER is not None:
    from ..parsers import YouTubeParser

    @on_command("ym", priority=3, block=True).handle()
    @UniHelper.exception_handler
    async def _(message: Message = CommandArg()):
        text = message.extract_plain_text()
        ytb_parser = cast(YouTubeParser, KEYWORD_PARSER_MAP["youtu.be"])
        _, matched = ytb_parser.search_url(text)
        if not matched:
            await UniMessage("请发送正确的油管链接").finish()

        url = matched.group(0)

        audio_path = await YTDLP_DOWNLOADER.download_audio(url)
        await UniMessage(UniHelper.record_seg(audio_path)).send()

        if pconfig.need_upload:
            await UniMessage(UniHelper.file_seg(audio_path)).send()
