import asyncio
import re

from nonebot import logger, on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule

from ..config import NICKNAME, plugin_cache_dir
from ..parsers.acfun import download_m3u8_videos, merge_ac_file_to_mp4, parse_acfun_url, parse_m3u8
from .filter import is_not_in_disabled_groups
from .helper import get_video_seg

acfun = on_keyword(keywords={"acfun.cn"}, rule=Rule(is_not_in_disabled_groups))


@acfun.handle()
async def _(event: MessageEvent) -> None:
    message: str = event.message.extract_plain_text().strip()
    matched = re.search(r"(?:ac=|/ac)(\d+)", message)
    if not matched:
        logger.info("acfun url is incomplete, ignored")
        return
    url = f"https://www.acfun.cn/v/ac{matched.group(1)}"
    url_m3u8s, video_name = await parse_acfun_url(url)
    await acfun.send(f"{NICKNAME}解析 | 猴山 - {video_name}")
    m3u8_full_urls, ts_names, output_file_name = await parse_m3u8(url_m3u8s)
    await asyncio.gather(*[download_m3u8_videos(url, i) for i, url in enumerate(m3u8_full_urls)])
    await merge_ac_file_to_mp4(ts_names, output_file_name)
    await acfun.send(get_video_seg(plugin_cache_dir / output_file_name))
