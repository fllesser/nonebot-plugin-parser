import json
import re
from typing import Any, Literal

from nonebot import logger
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.params import Depends
from nonebot.plugin.on import get_matcher_source
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot_plugin_alconna.uniseg import Hyper, UniMsg

from .filter import is_not_in_disabled_groups

PSR_KWD_KEY: Literal["_psr_kwd"] = "_psr_kwd"
PSR_EXTRACT_KEY: Literal["_psr_extract"] = "_psr_extract"
PSR_KWD_MATCHED_KEY: Literal["_psr_kwd_matched"] = "_psr_kwd_matched"


def ExtractText() -> str:
    return Depends(_extract_text)


def _extract_text(state: T_State) -> str | None:
    return state.get(PSR_EXTRACT_KEY)


def Keyword() -> str:
    return Depends(_keyword)


def _keyword(state: T_State) -> str | None:
    return state.get(PSR_KWD_KEY)


def KwdRegexMatched() -> re.Match[str]:
    return Depends(_kwd_regex_matched)


def _kwd_regex_matched(state: T_State) -> re.Match[str] | None:
    return state.get(PSR_KWD_MATCHED_KEY)


URL_KEY_MAPPING = {
    "detail_1": "qqdocurl",
    "news": "jumpUrl",
    "music": "jumpUrl",
}

CHAR_REPLACEMENTS = {"&#44;": ",", "\\": "", "&amp;": "&"}


def _clean_url(url: str) -> str:
    """清理 URL 中的特殊字符

    Args:
        url: 原始 URL

    Returns:
        str: 清理后的 URL
    """
    for old, new in CHAR_REPLACEMENTS.items():
        url = url.replace(old, new)
    return url


def _extract_json_url(hyper: Hyper) -> str | None:
    """处理 JSON 类型的消息段，提取 URL

    Args:
        json_seg: JSON 类型的消息段

    Returns:
        Optional[str]: 提取的 URL, 如果提取失败则返回 None
    """
    data = hyper.data
    raw_str = data.get("raw")

    if raw_str is None:
        return None
    # 处理转义字符
    raw_str = raw_str.replace("&#44;", ",")

    try:
        raw: dict[str, Any] = json.loads(raw_str)
    except json.JSONDecodeError:
        logger.exception("json 卡片解析失败")
        return None

    meta: dict[str, Any] | None = raw.get("meta")
    if not meta:
        return None

    for key1, key2 in URL_KEY_MAPPING.items():
        if item := meta.get(key1):
            if url := item.get(key2):
                return _clean_url(url)
    return None


@event_preprocessor
def extract_msg_text(message: UniMsg, state: T_State):
    if hyper := next(iter(message.get(Hyper, 1)), None):
        state[PSR_EXTRACT_KEY] = _extract_json_url(hyper)
        return

    # 提取纯文本
    if text := message.extract_plain_text().strip():
        state[PSR_EXTRACT_KEY] = text


class KeyPatternList(list[tuple[str, re.Pattern[str]]]):
    def __init__(self, *args: tuple[str, str | re.Pattern[str]]):
        super().__init__()
        for key, pattern in args:
            if isinstance(pattern, str):
                pattern = re.compile(pattern)
            self.append((key, pattern))


class KeywordRegexRule:
    """检查消息是否含有关键词, 有关键词进行正则匹配"""

    __slots__ = ("key_pattern_list",)

    def __init__(self, key_pattern_list: KeyPatternList):
        self.key_pattern_list = key_pattern_list

    def __repr__(self) -> str:
        return f"KeywordRegex(key_pattern_list={self.key_pattern_list})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, KeywordRegexRule) and self.key_pattern_list == other.key_pattern_list

    def __hash__(self) -> int:
        return hash(frozenset(self.key_pattern_list))

    async def __call__(self, state: T_State, text: str = ExtractText()) -> bool:
        if not text:
            return False
        for keyword, pattern in self.key_pattern_list:
            if keyword not in text:
                continue
            if matched := pattern.search(text):
                state[PSR_KWD_KEY] = keyword
                state[PSR_KWD_MATCHED_KEY] = matched
                return True
            logger.debug(f"keyword '{keyword}' is in '{text}', but not matched")
        return False


def keyword_regex(*args: tuple[str, str | re.Pattern[str]]) -> Rule:
    return Rule(KeywordRegexRule(KeyPatternList(*args)))


def on_keyword_regex(*args: tuple[str, str | re.Pattern[str]], priority: int = 5) -> type[Matcher]:
    matcher = Matcher.new(
        "message",
        is_not_in_disabled_groups & keyword_regex(*args),
        priority=priority,
        block=True,
        source=get_matcher_source(1),
    )
    return matcher
