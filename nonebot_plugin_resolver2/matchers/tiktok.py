import re, httpx, asyncio

from nonebot import on_keyword
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Event, Message

from .filter import is_not_in_disable_group
from .utils import get_video_seg
from ..data_source.ytdlp import get_video_info, ytdlp_download_video
from ..config import *


tiktok = on_keyword(keywords={"tiktok.com", "vt.tiktok.com", "vm.tiktok.com"}, rule = Rule(is_not_in_disable_group))

@tiktok.handle()
async def _(event: Event) -> None:
    """
        tiktok解析
    :param event:
    :return:
    """
    # 消息
    message: str = event.message.extract_plain_text().strip()
    url_reg = r"(http:|https:)\/\/(www|vt|vm).tiktok.com\/[A-Za-z\d._?%&+\-=\/#@]*"
    if match := re.search(url_reg, message):
        url = match.group(0)
        prefix = match.group(2)
    else:
        # not match, return
        return
    if prefix == "vt":
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True, proxies=PROXY)
        url = str(resp.url)
    elif prefix == "vm":
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={ "User-Agent": "facebookexternalhit/1.1" }, follow_redirects=True,
                              proxies=PROXY)
        url = str(resp.url)
    try:
        info = await get_video_info(url)
        await tiktok.send(f"{NICKNAME}解析 | TikTok - {info['title']}")
    except Exception as e:
        await tiktok.send(f"{NICKNAME}解析 | TikTok - 标题获取出错: {e}")
    try:
        video_name = await ytdlp_download_video(url = url)
        await tiktok.send(await get_video_seg(video_name))
    except Exception as e:
        await tiktok.send(f"下载失败 | {e}")


