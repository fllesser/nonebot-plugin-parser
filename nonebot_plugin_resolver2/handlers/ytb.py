import re

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import Arg, CommandArg
from .filter import resolve_filter
from .utils import auto_video_send
from ..core.ytdlp import get_video_title, ytdlp_download_video


from ..config import *

ytb = on_regex(
    r"(youtube.com|youtu.be)", priority=1
)

@ytb.handle()
@resolve_filter
async def ytb_handler(event: MessageEvent):
    url = re.search(
        r"(?:https?:\/\/)?(www\.)?youtube\.com\/[A-Za-z\d._?%&+\-=\/#]*|(?:https?:\/\/)?youtu\.be\/[A-Za-z\d._?%&+\-=\/#]*",
        str(event.message).strip())[0]

    try:
        title = await get_video_title(url, YTB_COOKIES_FILE, PROXY)
        await ytb.send(f"{NICKNAME}识别 | 油管 - {title}")
    except Exception as e:
        await ytb.send(f"{NICKNAME}识别 | 油管 - 标题获取出错: {e}")
    try:
        video_path = await ytdlp_download_video(
            url = url, path = (RPATH / 'temp').absolute(), type="ytb", cookiefile = YTB_COOKIES_FILE, proxy = PROXY)
        await auto_video_send(event, video_path)
    except Exception as e:
        await ytb.send(f"视频下载失败 | {e}")

# @ytb.got("type", prompt="您需要的是音频(0)还是视频(1)")
# async def _(type: Message = Arg()):
#     if int(type) == 1:
        