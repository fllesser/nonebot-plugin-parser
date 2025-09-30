import re

from nonebot_plugin_alconna import UniMessage

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import KuaishouParser
from .helper import UniHelper
from .preprocess import KeyPatternMatched, on_keyword_regex

parser = KuaishouParser()


kuaishou = on_keyword_regex(
    # - https://v.kuaishou.com/2yAnzeZ
    ("v.kuaishou.com", r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    # - https://www.kuaishou.com/short-video/3xhjgcmir24m4nm
    ("kuaishou", r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    # - https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc
    ("chenzhongtech", r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
)


@kuaishou.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    url = searched.group(0)

    parse_result = await parser.parse_url(url)

    msg = f"{NICKNAME}解析 | 快手 - {parse_result.title}-{parse_result.author}"

    if cover_url := parse_result.cover_url:
        # 下载封面
        cover_path = await DOWNLOADER.download_img(cover_url)
        msg += UniHelper.img_seg(cover_path)

    await UniMessage(msg).send()

    if video_url := parse_result.video_url:
        video_path = await DOWNLOADER.download_video(video_url)
        await UniMessage([UniHelper.video_seg(video_path)]).send()

    elif pic_urls := parse_result.pic_urls:
        img_paths = await DOWNLOADER.download_imgs_without_raise(pic_urls)
        segs = [UniHelper.img_seg(img_path) for img_path in img_paths]
        assert len(segs) > 0
        await UniHelper.send_segments(segs)
