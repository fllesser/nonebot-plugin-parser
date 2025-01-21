from nonebot import get_driver, require, get_plugin_config
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Literal

require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")
import nonebot_plugin_localstore as store  # noqa: E402
from nonebot_plugin_apscheduler import scheduler  # noqa: E402, F401

MatcherNames = Literal[
    "bilibili",
    "acfun",
    "douyin",
    "ytb",
    "kugou",
    "ncm",
    "twitter",
    "tiktok",
    "weibo",
    "xiaohongshu",
]

class Config(BaseModel):
    r_xhs_ck: str = ""
    r_bili_ck: str = ""
    r_ytb_ck: str = ""
    r_is_oversea: bool = False
    r_proxy: str = "http://127.0.0.1:7890"
    r_video_duration_maximum: int = 480
    r_disable_resolvers: List[MatcherNames] = []


plugin_cache_dir: Path = store.get_plugin_cache_dir()
plugin_config_dir: Path = store.get_plugin_config_dir()
plugin_data_dir: Path = store.get_plugin_data_dir()

# 配置加载
rconfig: Config = get_plugin_config(Config)

# cookie 存储位置
ytb_cookies_file = plugin_config_dir / "ytb_cookies.txt" if rconfig.r_ytb_ck else None
# bili_cookies_file = plugin_config_dir / 'bili_cookies.txt' if rconfig.r_bili_ck else None

# 全局名称
NICKNAME: Optional[str] = next(iter(get_driver().config.nickname), None)
# 根据是否为国外机器声明代理
PROXY: Optional[str] = None if rconfig.r_is_oversea else rconfig.r_proxy
# 哔哩哔哩限制的最大视频时长（默认8分钟）单位：秒
DURATION_MAXIMUM: int = rconfig.r_video_duration_maximum
