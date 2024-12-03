from nonebot import get_driver, logger

from nonebot.plugin import PluginMetadata
from .matchers import resolvers, commands
from .config import *
from .cookie import *


__plugin_meta__ = PluginMetadata(
    name="链接分享解析器重制版",
    description="NoneBot2 链接分享解析器插件, 支持的解析，BV号/链接/小程序/卡片，支持平台：b站，抖音，网易云，微博，小红书，youtube，tiktok，twitter等",
    usage="发送支持平台的(BV号/链接/小程序/卡片)即可",
    type="application",
    homepage="https://github.com/fllesser/nonebot-plugin-resolver2",
    config=Config,
    supported_adapters={ "~onebot.v11" }
)

@get_driver().on_startup
async def _():
    if rconfig.r_bili_ck:
        pass
    if rconfig.r_ytb_ck:
        save_cookies_to_netscape(rconfig.r_ytb_ck, YTB_COOKIES_FILE, 'youtube.com')
    # 处理黑名单 resovler
    for resolver in rconfig.r_disable_resolvers:
        if matcher := resolvers.get(resolver, None):
            matcher.destroy()
            logger.info(f"解析器 {resolver} 已销毁")

@scheduler.scheduled_job(
    "cron",
    hour=1,
    minute=0,
)
async def _():
    import os
    # 清理缓存目录中的文件
    for filename in os.listdir(plugin_cache_dir):
        file_path = os.path.join(plugin_cache_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # 删除文件或符号链接
            elif os.path.isdir(file_path):
                os.rmdir(file_path)  # 删除空目录
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
