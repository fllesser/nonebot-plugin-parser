import json
import re
from typing import Any, Literal

from nonebot import logger
from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.params import Depends
from nonebot.plugin.on import get_matcher_source
from nonebot.rule import Rule
from nonebot.typing import T_State

from .filter import is_not_in_disabled_groups

R_KEYWORD_KEY: Literal["_r_keyword"] = "_r_keyword"
R_EXTRACT_KEY: Literal["_r_extract"] = "_r_extract"
R_KEY_REGEX_MATCHED_KEY: Literal["_r_key_regex_matched"] = "_r_key_regex_matched"


def ExtractText() -> str:
    return Depends(_extract_text)


def _extract_text(state: T_State) -> str | None:
    return state.get(R_EXTRACT_KEY)


def Keyword() -> str:
    return Depends(_keyword)


def _keyword(state: T_State) -> str | None:
    return state.get(R_KEYWORD_KEY)


def KeyPatternMatched() -> re.Match[str]:
    return Depends(_key_pattern_matched)


def _key_pattern_matched(state: T_State) -> re.Match[str] | None:
    return state.get(R_KEY_REGEX_MATCHED_KEY)


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


try:
    from nonebot.adapters.onebot.v11 import Message, MessageSegment
except ImportError:
    Message = None


def _extract_json_url(json_seg: "MessageSegment") -> str | None:
    """处理 JSON 类型的消息段，提取 URL

    Args:
        json_seg: JSON 类型的消息段

    Returns:
        Optional[str]: 提取的 URL, 如果提取失败则返回 None
    """
    data_str: str | None = json_seg.data.get("data")
    if not data_str:
        return None

    # 处理转义字符
    data_str = data_str.replace("&#44;", ",")

    try:
        data: dict[str, Any] = json.loads(data_str)
    except json.JSONDecodeError:
        logger.exception("json 卡片解析失败")
        return None

    meta: dict[str, Any] | None = data.get("meta")
    if not meta:
        return None

    for key1, key2 in URL_KEY_MAPPING.items():
        if item := meta.get(key1):
            if url := item.get(key2):
                return _clean_url(url)
    return None


@event_preprocessor
def extract_msg_text(event: Event, state: T_State) -> None:
    try:
        message = event.get_message()
    except ValueError:
        return

    text: str | None = None

    # 提取json数据
    if (
        Message is not None
        and isinstance(message, Message)
        and (json_seg := next((seg for seg in message if seg.type == "json"), None))
    ):
        if url := _extract_json_url(json_seg):
            state[R_EXTRACT_KEY] = url
            return
    # 提取纯文本
    if text := message.extract_plain_text().strip():
        state[R_EXTRACT_KEY] = text


class UrlKeywordsRule:
    """检查消息是否含有关键词 增强版"""

    __slots__ = ("keywords",)

    def __init__(self, *keywords: str):
        self.keywords = keywords

    def __repr__(self) -> str:
        return f"UrlKeywords(keywords={self.keywords})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UrlKeywordsRule) and frozenset(self.keywords) == frozenset(other.keywords)

    def __hash__(self) -> int:
        return hash(frozenset(self.keywords))

    async def __call__(self, state: T_State, text: str = ExtractText()) -> bool:
        if not text:
            return False
        if key := next((k for k in self.keywords if k in text), None):
            state[R_KEYWORD_KEY] = key
            return True
        return False


def url_keywords(*keywords: str) -> Rule:
    return Rule(UrlKeywordsRule(*keywords))


def on_url_keyword(*keywords: str, priority: int = 5) -> type[Matcher]:
    matcher = Matcher.new(
        "message",
        is_not_in_disabled_groups & url_keywords(*keywords),
        priority=priority,
        block=True,
        source=get_matcher_source(1),
    )
    return matcher


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
                state[R_KEYWORD_KEY] = keyword
                state[R_KEY_REGEX_MATCHED_KEY] = matched
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
