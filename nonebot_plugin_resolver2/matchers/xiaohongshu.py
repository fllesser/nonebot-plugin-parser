import re

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME
from ..download import download_imgs_without_raise, download_video
from ..exception import handle_exception
from ..parsers.xiaohongshu import parse_url
from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg, send_segments
from .preprocess import ExtractText, r_keywords

xiaohongshu = on_message(rule=is_not_in_disabled_groups & r_keywords("xiaohongshu.com", "xhslink.com"))


@xiaohongshu.handle()
@handle_exception(xiaohongshu)
async def _(text: str = ExtractText()):
    matched = re.search(
        r"(http:|https:)\/\/(xhslink|(www\.)xiaohongshu).com\/[A-Za-z\d._?%&+\-=\/#@]*",
        text,
    )
    if not matched:
        logger.info(f"{text} ignored")
        return
    # 解析 url
    title_desc, img_urls, video_url = await parse_url(matched.group(0))
    # 如果是图文
    if img_urls:
        await xiaohongshu.send(f"{NICKNAME}解析 | 小红书 - 图文")
        img_path_list = await download_imgs_without_raise(img_urls)
        # 发送图片
        segs: list[MessageSegment | Message | str] = [
            title_desc,
            *(get_img_seg(img_path) for img_path in img_path_list),
        ]
        await send_segments(segs)
    # 如果是视频
    elif video_url:
        await xiaohongshu.send(f"{NICKNAME}解析 | 小红书 - 视频 - {title_desc}")
        video_path = await download_video(video_url)
        await xiaohongshu.finish(get_video_seg(video_path))
