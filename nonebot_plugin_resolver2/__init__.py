import os
import shutil

from nonebot import get_driver, require, logger
from nonebot.plugin import PluginMetadata

from .matchers import resolvers, commands
from .config import *
from .cookie import *

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

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
                logger.info(f"Created directory: {path}")

    paths = [rpath, temp_path, video_path, audio_path, image_path, rpath / "cookie"] 
    # 检查并创建目录 create_directories(paths)
    create_directories(paths)
    
    if rconfig.r_bili_ck:
        pass
        # cookie_dict = cookies_str_to_dict(rconfig.r_bili_ck)
        # if cookie_dict["SESSDATA"]:
        #     logger.info(f"bilibili credential format sucess from cookie")
        # else:
        #     logger.error(f"配置的 bili_ck 未包含 SESSDATA 项，可能无效")
        # save_cookies_to_netscape(rconfig.bili_ck, bili_cookies_file, 'bilibili.com')
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
    temp_path = rpath / "temp"
    if not os.path.exists(temp_path):
        logger.error(f"The folder {temp_path} does not exist.")
        return
    for filename in os.listdir(temp_path):
        file_path = os.path.join(temp_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # 删除文件或链接
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # 递归删除文件夹
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")
    logger.info(f"{temp_path.absolute()} 已清理")
