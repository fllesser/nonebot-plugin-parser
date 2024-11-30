from nonebot import get_driver
from pydantic import BaseModel
from nonebot import get_plugin_config
from pathlib import Path
from bilibili_api import Credential

class Config(BaseModel):
    r_xhs_ck: str = ''
    r_douyin_ck: str = ''
    r_bili_ck: str = ''
    r_ytb_ck: str = ''
    r_is_oversea: bool = False
    r_proxy: str = 'http://127.0.0.1:7890'
    r_video_duration_maximum: int = 480
    r_black_resolvers: list[str] = []

# 插件数据目录
RPATH: Path = Path() / 'data' /'nonebot-plugin-resolver'

VIDEO_PATH: Path = RPATH / "temp" / "video"
AUDIO_PATH: Path = RPATH / "temp" / "audio"
IMAGE_PATH: Path = RPATH / "temp" / "image"

YTB_COOKIES_FILE = (RPATH / 'cookie' / 'ytb_cookies.txt').absolute()
BILI_COOKIES_FILE = (RPATH / 'cookie' / 'bili_cookies.txt').absolute()
# 配置加载
RCONFIG: Config = get_plugin_config(Config)
# 全局名称
NICKNAME: str = next(iter(get_driver().config.nickname))
# 根据是否为国外机器声明代理
PROXY: str = "" if not RCONFIG.r_is_oversea else RCONFIG.r_proxy
# 哔哩哔哩限制的最大视频时长（默认8分钟）单位：秒
DURATION_MAXIMUM: int = RCONFIG.r_video_duration_maximum