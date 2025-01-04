from typing import (
    List,
    Literal,
    get_args
)
from ..constant import MatcherNames
# MatcherNames = Literal["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xiaohongshu"]

modules: List[MatcherNames] = list(get_args(MatcherNames))
for module in modules:
    exec(f"from .{module} import {module}")
    
resolvers = {module: eval(module) for module in modules}
