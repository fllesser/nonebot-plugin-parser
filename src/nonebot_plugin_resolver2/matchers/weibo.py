from nonebot import on_message

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import WeiBoParser
from .filter import is_not_in_disabled_groups
from .helper import obhelper
from .preprocess import ExtractText, r_keywords

weibo_parser = WeiBoParser()

weibo = on_message(
    rule=is_not_in_disabled_groups & r_keywords("weibo.com", "m.weibo.cn"),
    priority=5,
)


@weibo.handle()
@handle_exception()
async def _(text: str = ExtractText()):
    video_info = await weibo_parser.parse_share_url(text)

    await weibo.send(f"{NICKNAME}解析 | 微博 - {video_info.title} - {video_info.author}")

    if video_info.video_url:
        video_path = await DOWNLOADER.download_video(video_info.video_url, ext_headers=weibo_parser.ext_headers)
        await weibo.finish(obhelper.video_seg(video_path))

    if video_info.pic_urls:
        image_paths = await DOWNLOADER.download_imgs_without_raise(
            video_info.pic_urls, ext_headers=weibo_parser.ext_headers
        )
        if image_paths:
            await obhelper.send_segments([obhelper.img_seg(path) for path in image_paths])
