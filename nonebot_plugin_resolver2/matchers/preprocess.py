import json
from typing import Any, Literal

from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.log import logger
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


@event_preprocessor
def _(event: MessageEvent, state: T_State) -> None:
    message = event.get_message()
    text: str | None = None

    # 提取纯文本
    if text := message.extract_plain_text().strip():
        state[R_EXTRACT_KEY] = text
        return

    # 提取json数据
    json_seg = next((seg for seg in message if seg.type == "json"), None)
    if json_seg is None:
        return

    data_str: str | None = json_seg.data.get("data")

    if not data_str:
        return
    # 处理转义字符
    data_str = data_str.replace("&#44;", ",")

    try:
        data: dict[str, Any] = json.loads(data_str)
    except json.JSONDecodeError:
        logger.debug("json 卡片解析失败")
        return

    meta: dict[str, Any] | None = data.get("meta", None)
    if meta is None:
        return

    # 提取链接
    if detail := meta.get("detail_1"):
        text = detail.get("qqdocurl")
    elif news := meta.get("news"):
        text = news.get("jumpUrl")
    elif music := meta.get("music"):
        text = music.get("jumpUrl")
    else:
        return

    if not text:
        return
    state[R_EXTRACT_KEY] = text.replace("\\", "").replace("&amp;", "&")


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
