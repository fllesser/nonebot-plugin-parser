import json
from typing import Any, Literal

from nonebot import logger
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.message import event_preprocessor
from nonebot.params import Depends
from nonebot.rule import Rule
from nonebot.typing import T_State

R_KEYWORD_KEY: Literal["_r_keyword"] = "_r_keyword"
R_EXTRACT_KEY: Literal["_r_extract"] = "_r_extract"


def ExtractText() -> str:
    return Depends(_extact_text)


def _extact_text(state: T_State) -> str:
    return state.get(R_EXTRACT_KEY) or ""


def Keyword() -> str:
    return Depends(_keyword)


def _keyword(state: T_State) -> str:
    return state.get(R_KEYWORD_KEY) or ""


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


def _extract_json_url(json_seg: MessageSegment) -> str | None:
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
        logger.debug("json 卡片解析失败")
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
def extract_msg_text(event: MessageEvent, state: T_State) -> None:
    message = event.get_message()
    text: str | None = None

    # 提取json数据
    if json_seg := next((seg for seg in message if seg.type == "json"), None):
        if url := _extract_json_url(json_seg):
            state[R_EXTRACT_KEY] = url
    # 提取纯文本
    if text := message.extract_plain_text().strip():
        state[R_EXTRACT_KEY] = text


class RKeywordsRule:
    """检查消息是否含有关键词 增强版"""

    __slots__ = ("keywords",)

    def __init__(self, *keywords: str):
        self.keywords = keywords

    def __repr__(self) -> str:
        return f"RKeywords(keywords={self.keywords})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RKeywordsRule) and frozenset(self.keywords) == frozenset(other.keywords)

    def __hash__(self) -> int:
        return hash(frozenset(self.keywords))

    async def __call__(self, state: T_State, text: str = ExtractText()) -> bool:
        if not text:
            return False
        if key := next((k for k in self.keywords if k in text), None):
            state[R_KEYWORD_KEY] = key
            return True
        return False


def r_keywords(*keywords: str) -> Rule:
    return Rule(RKeywordsRule(*keywords))
