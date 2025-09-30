import re

from nonebot_plugin_alconna import UniMessage

from ..config import NICKNAME
from ..exception import handle_exception
from ..parsers import AcfunParser
from .helper import UniHelper
from .preprocess import KeyPatternMatched, on_keyword_regex

acfun = on_keyword_regex(("acfun.cn", r"(?:ac=|/ac)(\d+)"))

parser = AcfunParser()


@acfun.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    acid = int(searched.group(1))
    url = f"https://www.acfun.cn/v/ac{acid}"
    m3u8_url, video_desc = await parser.parse_url(url)
    await acfun.send(f"{NICKNAME}解析 | 猴山 - {video_desc}")

    video_file = await parser.download_video(m3u8_url, acid)
    await UniMessage([UniHelper.video_seg(video_file)]).send()
