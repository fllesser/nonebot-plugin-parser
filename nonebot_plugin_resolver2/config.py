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
    r_disable_resolvers: list[str] = []

# 插件数据目录
rpath: Path = Path() / 'data' /'nonebot-plugin-resolver2'

temp_path: Path = rpath / "temp"
video_path: Path = temp_path / "video"
audio_path: Path = temp_path / "audio"
image_path: Path = temp_path / "image"
# 配置加载
rconfig: Config = get_plugin_config(Config)

# cookie 存储位置
YTB_COOKIES_FILE = rpath / 'cookie' / 'ytb_cookies.txt'
BILI_COOKIES_FILE = rpath / 'cookie' / 'bili_cookies.txt'

# 全局名称
NICKNAME: str = next(iter(get_driver().config.nickname), "")
# 根据是否为国外机器声明代理
PROXY: str = None if rconfig.r_is_oversea else rconfig.r_proxy
# 哔哩哔哩限制的最大视频时长（默认8分钟）单位：秒
DURATION_MAXIMUM: int = rconfig.r_video_duration_maximum