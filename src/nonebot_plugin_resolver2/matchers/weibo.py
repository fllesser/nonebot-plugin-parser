import json

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import MessageEvent

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import WeiBoParser
from .filter import is_not_in_disabled_groups
from .helper import obhelper
from .preprocess import r_keywords

weibo_parser = WeiBoParser()

weibo = on_message(
    rule=is_not_in_disabled_groups & r_keywords("weibo.com", "m.weibo.cn"),
    priority=5,
)


@weibo.handle()
@handle_exception()
async def _(event: MessageEvent):
    if len(event.message) == 1 and event.message[0].type == "json":  # 处理QQ小程序消息
        try:
            data = json.loads(event.message[0].data["data"])
            message = data["meta"]["detail_1"]["qqdocurl"]
        except Exception as e:
            logger.error(f"处理QQ小程序消息时发生错误: {e}")
            return
    else:
        message = event.message.extract_plain_text().strip()
    video_info = await weibo_parser.parse_share_url(message)

    ext_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
        "referer": "https://weibo.com/",
    }

    await weibo.send(f"{NICKNAME}解析 | 微博 - {video_info.title} - {video_info.author}")
    if video_info.video_url:
        video_path = await DOWNLOADER.download_video(video_info.video_url, ext_headers=ext_headers)
        await weibo.finish(obhelper.video_seg(video_path))
    if video_info.pic_urls:
        image_paths = await DOWNLOADER.download_imgs_without_raise(video_info.pic_urls, ext_headers=ext_headers)
        if image_paths:
            await obhelper.send_segments([obhelper.img_seg(path) for path in image_paths])
