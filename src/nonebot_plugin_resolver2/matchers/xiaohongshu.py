import re

from nonebot_plugin_alconna import UniMessage

from ..config import NICKNAME
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import XiaoHongShuParser
from .helper import UniHelper
from .preprocess import KeyPatternMatched, on_keyword_regex

xiaohongshu = on_keyword_regex(
    ("xiaohongshu.com", r"https?://(?:www\.)?xiaohongshu\.com/[A-Za-z0-9._?%&+=/#@-]*"),
    ("xhslink.com", r"https?://xhslink\.com/[A-Za-z0-9._?%&+=/#@-]*"),
)

parser = XiaoHongShuParser()


@xiaohongshu.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    # 解析 url
    parse_result = await parser.parse_url(searched.group(0))
    msg_prefix = f"{NICKNAME}解析 | 小红书 - "
    # 如果是图文
    if pic_urls := parse_result.pic_urls:
        await xiaohongshu.send(f"{msg_prefix}图文")
        img_path_list = await DOWNLOADER.download_imgs_without_raise(pic_urls)
        # 发送图片
        segs = [parse_result.title, *[UniHelper.img_seg(img_path) for img_path in img_path_list]]
        await UniHelper.send_segments(segs)
    # 如果是视频
    elif video_url := parse_result.video_url:
        msg = f"{msg_prefix}视频\n标题: {parse_result.title}"
        if cover_url := parse_result.cover_url:
            cover_path = await DOWNLOADER.download_img(cover_url)
            await UniMessage(msg + UniHelper.img_seg(cover_path)).send()
        else:
            await UniMessage(msg).send()
        video_path = await DOWNLOADER.download_video(video_url)
        await UniMessage([UniHelper.video_seg(video_path)]).send()
