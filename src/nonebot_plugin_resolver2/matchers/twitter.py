import asyncio
from pathlib import Path
import re
from typing import Any

from nonebot_plugin_alconna import UniMessage

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import TwitterParser
from ..parsers.data import ImageContent, VideoContent
from .helper import UniHelper
from .preprocess import KeyPatternMatched, on_keyword_regex

twitter = on_keyword_regex(("x.com", r"https?://x.com/[0-9-a-zA-Z_]{1,20}/status/([0-9]+)"))


@twitter.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    x_url = searched.group(0)

    await twitter.send(f"{NICKNAME}解析 | 小蓝鸟")

    content = await TwitterParser.parse_x_url(x_url)

    if isinstance(content, VideoContent):
        video_path = await DOWNLOADER.download_video(content.video_url)
        await UniMessage([UniHelper.video_seg(video_path)]).send()

    elif isinstance(content, ImageContent):
        img_paths = await DOWNLOADER.download_imgs_without_raise(content.pic_urls)
        if len(img_paths) == 0:
            await twitter.finish("图片下载失败")
        if (count := len(img_paths)) < len(content.pic_urls):
            await twitter.send(f"部分图片下载失败，成功下载 {count} 张图片")
        segs: list[Any] = [UniHelper.img_seg(img_path) for img_path in img_paths]
        # 存在 gif
        if len(content.dynamic_urls) > 0:
            video_paths = await asyncio.gather(
                *[DOWNLOADER.download_video(url) for url in content.dynamic_urls], return_exceptions=True
            )
            segs.extend(UniHelper.video_seg(p) for p in video_paths if isinstance(p, Path))

        await UniHelper.send_segments(segs)
