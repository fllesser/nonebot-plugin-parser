import asyncio
import re

from nonebot import logger, on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule

from ..config import NICKNAME
from ..download import download_file_by_stream
from ..parsers.acfun import merge_acs_to_mp4, parse_acfun_url, parse_m3u8
from .filter import is_not_in_disabled_groups
from .helper import get_video_seg

acfun = on_keyword(keywords={"acfun.cn"}, rule=Rule(is_not_in_disabled_groups))


@acfun.handle()
async def _(event: MessageEvent) -> None:
    message: str = event.message.extract_plain_text().strip()
    matched = re.search(r"(?:ac=|/ac)(\d+)", message)
    if not matched:
        logger.info("acfun 链接中不包含 acid, 忽略")
        return
    acid = int(matched.group(1))
    url = f"https://www.acfun.cn/v/ac{acid}"
    m3u8s_url, video_desc = await parse_acfun_url(url)
    await acfun.send(f"{NICKNAME}解析 | 猴山 - {video_desc}")

    m3u8_full_urls = await parse_m3u8(m3u8s_url)
    ts_path_lst = await asyncio.gather(*[download_file_by_stream(url) for url in m3u8_full_urls])
    video_file = await merge_acs_to_mp4(acid, ts_path_lst)
    await acfun.send(get_video_seg(video_file))
