from nonebot import get_driver, require, get_plugin_config
require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
import nonebot_plugin_localstore as store
from pydantic import BaseModel
from pathlib import Path

class Config(BaseModel):
    r_xhs_ck: str = ''
    r_bili_ck: str = ''
    r_ytb_ck: str = ''
    r_is_oversea: bool = False
    r_proxy: str = 'http://127.0.0.1:7890'
    r_video_duration_maximum: int = 480
    r_disable_resolvers: list[str] = []


plugin_cache_dir: Path = store.get_plugin_cache_dir()
plugin_config_dir: Path = store.get_plugin_config_dir()
plugin_data_dir: Path = store.get_plugin_data_dir()

# 配置加载
rconfig: Config = get_plugin_config(Config)

# cookie 存储位置
YTB_COOKIES_FILE = plugin_config_dir / 'ytb_cookies.txt' if rconfig.r_ytb_ck else None
BILI_COOKIES_FILE = plugin_config_dir / 'bili_cookies.txt' if rconfig.r_bili_ck else None

# 全局名称
NICKNAME: str = next(iter(get_driver().config.nickname), "")
# 根据是否为国外机器声明代理
PROXY: str = None if rconfig.r_is_oversea else rconfig.r_proxy
# 哔哩哔哩限制的最大视频时长（默认8分钟）单位：秒
DURATION_MAXIMUM: int = rconfig.r_video_duration_maximum