from nonebot import get_driver, logger
from nonebot.plugin import PluginMetadata

from .config import (
    Config,
    plugin_cache_dir,
    rconfig,
    scheduler,
    ytb_cookies_file,
)
from .cookie import save_cookies_to_netscape
from .matchers import resolvers

__plugin_meta__ = PluginMetadata(
    name="链接分享解析 ob 版(不再维护)",
    description="onebot 版, 不再维护, 请使用 nonebot-plugin-parser",
    usage="发送支持平台的(BV号/链接/小程序/卡片)即可",
    type="application",
    homepage="https://github.com/fllesser/nonebot-plugin-parser/tree/resolver2",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "fllesser",
        "email": "fllessive@gmail.com",
        "homepage": "https://github.com/fllesser/nonebot-plugin-parser/tree/resolver2",
    },
)


@get_driver().on_startup
async def _():
    if rconfig.r_ytb_ck:
        save_cookies_to_netscape(rconfig.r_ytb_ck, ytb_cookies_file, "youtube.com")
        logger.debug(f"保存 youtube cookie 到 {ytb_cookies_file}")

    destroy_resolvers: list[str] = []
    if not rconfig.r_xhs_ck:
        if xiaohongshu := resolvers.pop("xiaohongshu", None):
            xiaohongshu.destroy()
            logger.warning("未配置小红书 cookie, 小红书解析已关闭")
            destroy_resolvers.append("xiaohongshu")

    # 关闭全局禁用的解析
    for resolver in rconfig.r_disable_resolvers:
        if matcher := resolvers.get(resolver, None):
            matcher.destroy()
            destroy_resolvers.append(resolver)
    if destroy_resolvers:
        logger.warning(f"已关闭解析: {', '.join(destroy_resolvers)}")


@scheduler.scheduled_job("cron", hour=1, minute=0, id="resolver2-clean-local-cache")
async def clean_plugin_cache():
    import asyncio

    from .download.utils import safe_unlink

    try:
        files = [f for f in plugin_cache_dir.iterdir() if f.is_file()]
        if not files:
            logger.info("No cache files to clean")
            return

        # 并发删除文件
        tasks = [safe_unlink(file) for file in files]
        await asyncio.gather(*tasks)

        logger.success(f"Successfully cleaned {len(files)} cache files")
    except Exception:
        logger.exception("Error while cleaning cache files")
