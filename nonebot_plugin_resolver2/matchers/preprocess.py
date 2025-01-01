import json

from typing import Literal
from nonebot.log import logger
from nonebot.message import event_preprocessor
from nonebot.typing import T_State
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import MessageEvent


R_KEYWORD_KEY: Literal["_r_keyword"] = "_r_keyword"
R_EXTRACT_KEY: Literal["_r_extract"] = "_r_extract"


def find_https_links(data):
    links = ""

    def recursive_search(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, dict) or isinstance(value, list):
                    recursive_search(value)
                elif isinstance(value, str) and value.startswith("https"):
                    links += ' ' + value
        elif isinstance(d, list):
            for item in d:
                recursive_search(item)

    recursive_search(data)
    return links


@event_preprocessor
def _(event: MessageEvent, state: T_State): 
    message = event.get_message()
    text = message.extract_plain_text().strip()
    if json_seg := [seg for seg in message if seg.type == 'json']:
        try:
            data_str = json_seg[0].data.get('data').replace('&#44;', ',')
            data = json.loads(data_str)
            meta = data.get('meta')
            if detail := meta.get('detail_1'):
                text = detail.get('qqdocurl')
            elif news := meta.get('news'):
                text = news.get('jumpUrl')
            else:
                text = find_https_links(meta)
                    
            text = text.replace('\\', '').replace("&amp;", "&")
        except Exception:
            pass
    state[R_EXTRACT_KEY] = text




class RKeywordsRule:
    """检查消息是否含有关键词 增强版"""

    __slots__ = ("keywords",)

    def __init__(self, *keywords: str):
        self.keywords = keywords

    def __repr__(self) -> str:
        return f"RKeywords(keywords={self.keywords})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RKeywordsRule) and frozenset(
            self.keywords
        ) == frozenset(other.keywords)

    def __hash__(self) -> int:
        return hash(frozenset(self.keywords))

    async def __call__(self, state: T_State) -> bool:
        text = state.get(R_EXTRACT_KEY)
        if not text:
            return False
        if key := next((k for k in self.keywords if k in text), None):
            state[R_KEYWORD_KEY] = key
            return True
        return False
        
        
def r_keywords(*keywords: str) -> Rule:
    return Rule(RKeywordsRule(*keywords))