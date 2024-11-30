import re
import asyncio

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Message, Event

from .filter import resolve_filter
from .utils import auto_video_send
from ..core.acfun import parse_url, download_m3u8_videos, parse_m3u8, merge_ac_file_to_mp4

from ..config import *

acfun = on_regex(r"(acfun.cn)")

@acfun.handle()
@resolve_filter
async def acfun_handler(event: Event) -> None:
    """
        acfun解析
    :param event:
    :return:
    """
    # 消息
    inputMsg: str = str(event.message).strip()

    # 短号处理
    if "m.acfun.cn" in inputMsg:
        inputMsg = f"https://www.acfun.cn/v/ac{re.search(r'ac=([^&?]*)', inputMsg)[1]}"

    url_m3u8s, video_name = parse_url(inputMsg)
    await acfun.send(Message(f"{NICKNAME}识别：猴山，{video_name}"))
    m3u8_full_urls, ts_names, output_folder_name, output_file_name = parse_m3u8(url_m3u8s)
    # logger.info(output_folder_name, output_file_name)
    await asyncio.gather(*[download_m3u8_videos(url, i) for i, url in enumerate(m3u8_full_urls)])
    merge_ac_file_to_mp4(ts_names, output_file_name)
    await auto_video_send(event, f"{VIDEO_PATH.absolute()}/{output_file_name}")

