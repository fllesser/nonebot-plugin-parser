from pathlib import Path
from typing import Literal

from nonebot import get_driver, get_plugin_config, require
from pydantic import BaseModel

require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: F401
import nonebot_plugin_localstore as store

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
    # 小红书 cookies
    r_xhs_ck: str = ""
    # bilibili cookies
    r_bili_ck: str = ""
    # youtube cookies
    r_ytb_ck: str = ""
    # 代理
    r_proxy: str | None = None
    # 是否需要上传音频文件
    r_need_upload: bool = False
    # 4 条以内消息，是否需要合并转发
    r_need_forward: bool = True
    # 是否使用 base64 编码发送图片，音频，视频
    r_use_base64: bool = False
    # 资源最大大小 默认 100 单位 MB
    r_max_size: int = 100
    # 视频最大时长
    r_video_duration_maximum: int = 480
    # 禁止的解析器
    r_disable_resolvers: list[MatcherNames] = []


plugin_cache_dir: Path = store.get_plugin_cache_dir()
plugin_config_dir: Path = store.get_plugin_config_dir()
plugin_data_dir: Path = store.get_plugin_data_dir()

# 配置加载
rconfig: Config = get_plugin_config(Config)

# cookie 存储位置
ytb_cookies_file: Path = plugin_config_dir / "ytb_cookies.txt"

# 全局名称
NICKNAME: str = next(iter(get_driver().config.nickname), "")
# 根据是否为国外机器声明代理
PROXY: str | None = rconfig.r_proxy
# 哔哩哔哩限制的最大视频时长（默认8分钟）单位：秒
DURATION_MAXIMUM: int = rconfig.r_video_duration_maximum
# 资源最大大小
MAX_SIZE: int = rconfig.r_max_size
# 是否需要上传音频文件
NEED_UPLOAD: bool = rconfig.r_need_upload
# 是否需要合并转发
NEED_FORWARD: bool = rconfig.r_need_forward
# 是否使用 base64 编码发送图片，音频，视频
USE_BASE64: bool = rconfig.r_use_base64
