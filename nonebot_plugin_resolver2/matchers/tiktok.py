import re
import aiohttp

from nonebot import on_keyword
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import MessageEvent

from .filter import is_not_in_disable_group
from .utils import get_video_seg
from ..download.ytdlp import get_video_info, ytdlp_download_video
from ..config import PROXY, NICKNAME


tiktok = on_keyword(keywords={"tiktok.com"}, rule=Rule(is_not_in_disable_group))


@tiktok.handle()
async def _(event: MessageEvent):
    # 消息
    message: str = event.message.extract_plain_text().strip()
    url_reg = r"(?:http:|https:)\/\/(www|vt|vm).tiktok.com\/[A-Za-z\d._?%&+\-=\/#@]*"
    if match := re.search(url_reg, message):
        url = match.group(0)
        prefix = match.group(1)
    else:
        return

    if prefix == "vt" or prefix == "vm":
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=False, proxy=PROXY) as resp:
                url = resp.headers.get("Location")
    assert url
    try:
        info = await get_video_info(url)
        await tiktok.send(f"{NICKNAME}解析 | TikTok - {info['title']}")
    except Exception as e:
        await tiktok.send(f"{NICKNAME}解析 | TikTok - 标题获取出错: {e}")

    try:
        video_path = await ytdlp_download_video(url=url)
        res = await get_video_seg(video_path)
    except Exception as e:
        res = f"下载视频失败 | {e}"

    await tiktok.send(res)
