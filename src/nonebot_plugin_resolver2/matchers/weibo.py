from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import WeiBoParser
from .helper import obhelper
from .preprocess import ExtractText, on_url_keyword

weibo_parser = WeiBoParser()

weibo = on_url_keyword("weibo.com", "m.weibo.cn")


@weibo.handle()
@handle_exception()
async def _(text: str = ExtractText()):
    parse_result = await weibo_parser.parse_share_url(text)

    await weibo.send(f"{NICKNAME}解析 | 微博 - {parse_result.title} - {parse_result.author}")

    if video_url := parse_result.video_url:
        video_path = await DOWNLOADER.download_video(video_url, ext_headers=weibo_parser.ext_headers)
        await weibo.finish(obhelper.video_seg(video_path))

    elif pic_urls := parse_result.pic_urls:
        image_paths = await DOWNLOADER.download_imgs_without_raise(pic_urls, ext_headers=weibo_parser.ext_headers)
        if image_paths:
            await obhelper.send_segments([obhelper.img_seg(path) for path in image_paths])
