import os
import shutil

from nonebot import get_driver, require, logger
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from nonebot.plugin import PluginMetadata
from .matchers import resolvers, commands
from .config import *
from .cookie import *



__plugin_meta__ = PluginMetadata(
    name="流媒体链接分享解析器重置版",
    description="NoneBot2 链接分享解析器插件, 支持的解析，BV号/链接/小程序/卡片，支持平台：b站，抖音，网易云，微博，小红书，youtube，tiktok，twitter等",
    usage="发送支持平台的(BV号/链接/小程序/卡片)即可",
    type="application",
    homepage="https://github.com/fllesser/nonebot-plugin-resolver2",
    config=Config,
    supported_adapters={ "~onebot.v11" }
)

@get_driver().on_startup
async def _():
    # 创建目录的函数
    def create_directories(paths):
        for path in paths:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建文件夹: {path}")

    paths = [rpath, temp_path, video_path, audio_path, image_path, rpath / "cookie"] 
    # 检查并创建目录 create_directories(paths)
    create_directories(paths)
    
    if rconfig.r_bili_ck:
        pass

    if rconfig.r_ytb_ck:
        save_cookies_to_netscape(rconfig.r_ytb_ck, YTB_COOKIES_FILE, 'youtube.com')
    # 处理黑名单 resovler
    for resolver in rconfig.r_disable_resolvers:
        if matcher := resolvers[resolver]:
            matcher.destroy()
            logger.info(f"解析器 {resolver} 已销毁")

@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=0,
)
async def _():
    directories_to_clean = [temp_path, video_path, audio_path, image_path]
    def clean_directory(path: Path): 
        for item in path.iterdir(): 
            if item.is_file(): 
                item.unlink()
            else:
                # 递归删除子目录中的文件 
                clean_directory(item)
                # 如果子目录为空，删除子目录 
                if not any(item.iterdir()):
                    item.rmdir()
    for path in directories_to_clean:
        clean_directory(path)
        logger.info(f"{path} 已清理")