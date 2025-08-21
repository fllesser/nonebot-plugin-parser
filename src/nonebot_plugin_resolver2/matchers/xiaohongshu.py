import re

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import XiaoHongShuParser
from .helper import obhelper
from .preprocess import KeyPatternMapping, KeyPatternMatched, on_keyword_regex

KEY_PATTERN_MAPPING = KeyPatternMapping(
    ("xiaohongshu.com", r"https?://(?:www\.)?xiaohongshu\.com/[^\s]*"),
    ("xhslink.com", r"(http:|https:)\/\/xhslink.com\/[A-Za-z\d._?%&+\-=\/#@]*"),
)

xiaohongshu = on_keyword_regex(KEY_PATTERN_MAPPING)

parser = XiaoHongShuParser()


@xiaohongshu.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    # 解析 url
    parse_result = await parser.parse_url(searched.group(0))
    # 如果是图文
    if pic_urls := parse_result.pic_urls:
        await xiaohongshu.send(f"{NICKNAME}解析 | 小红书 - 图文")
        img_path_list = await DOWNLOADER.download_imgs_without_raise(pic_urls)
        # 发送图片
        segs: list[MessageSegment | Message | str] = [
            parse_result.title,
            *(obhelper.img_seg(img_path) for img_path in img_path_list),
        ]
        await obhelper.send_segments(segs)
    # 如果是视频
    elif video_url := parse_result.video_url:
        await xiaohongshu.send(f"{NICKNAME}解析 | 小红书 - 视频 - {parse_result.title}")
        video_path = await DOWNLOADER.download_video(video_url)
        await xiaohongshu.finish(obhelper.video_seg(video_path))
