import re

from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from nonebot.log import logger
from nonebot.plugin.on import on_message

from nonebot_plugin_resolver2.config import NICKNAME
from nonebot_plugin_resolver2.download import download_imgs_without_raise
from nonebot_plugin_resolver2.parsers.xiaohongshu import parse_url

from .filter import is_not_in_disabled_groups
from .preprocess import ExtractText, r_keywords
from .utils import get_video_seg, send_segments

xiaohongshu = on_message(rule=is_not_in_disabled_groups & r_keywords("xiaohongshu.com", "xhslink.com"))


@xiaohongshu.handle()
async def _(bot: Bot, text: str = ExtractText()):
    matched = re.search(
        r"(http:|https:)\/\/(xhslink|(www\.)xiaohongshu).com\/[A-Za-z\d._?%&+\-=\/#@]*",
        text,
    )
    if not matched:
        logger.info(f"{text} ignored")
        return
    try:
        title_desc, img_urls, video_url = await parse_url(matched.group(0))
    except Exception as e:
        logger.error(f"解析小红书失败: {e}")
        await xiaohongshu.finish(f"{NICKNAME}解析 | 小红书 - 笔记不存在或 cookie 过期")
    if img_urls:
        await xiaohongshu.send(f"{NICKNAME}解析 | 小红书 - 图文")
        img_path_list = await download_imgs_without_raise(img_urls)
        # 发送图片
        segs = [title_desc] + [MessageSegment.image(img_path) for img_path in img_path_list]
        await send_segments(xiaohongshu, segs)
        await xiaohongshu.finish()
    elif video_url:
        await xiaohongshu.send(f"{NICKNAME}解析 | 小红书 - 视频 - {title_desc}")
        await xiaohongshu.finish(await get_video_seg(url=video_url))
