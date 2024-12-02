import re

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment, Bot
from nonebot.typing import T_State
from nonebot.params import Arg
from .filter import resolve_filter
from .utils import get_video_seg, upload_both
from ..core.ytdlp import *
from ..config import *

ytb = on_regex(
    r"(youtube.com|youtu.be)", priority=1
)

@ytb.handle()
@resolve_filter
async def _(event: MessageEvent, state: T_State):
    url = re.search(
        r"(?:https?:\/\/)?(www\.)?youtube\.com\/[A-Za-z\d._?%&+\-=\/#]*|(?:https?:\/\/)?youtu\.be\/[A-Za-z\d._?%&+\-=\/#]*",
        str(event.message).strip())[0]
    try:
        info_dict = await get_video_info(url, YTB_COOKIES_FILE)
        title = info_dict.get('title', "未知")
        await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")
    except Exception as e:
        await ytb.send(f"{NICKNAME}解析 | 油管 - 标题获取出错: {e}")
    state["url"] = url

@resolve_filter
@ytb.got("type", prompt="您需要下载音频(0)，还是视频(1)")
async def _(bot: Bot, event: MessageEvent, state: T_State, type: Message = Arg()):
    url: str = state["url"]
    try:
        if int(type.extract_plain_text()) == 1:
            video_name = await ytdlp_download_video(url = url, cookiefile = YTB_COOKIES_FILE)
            await ytb.send(await get_video_seg(video_name))
        else: 
            audio_name = await ytdlp_download_audio(url = url, cookiefile = YTB_COOKIES_FILE)
            # seg = get_file_seg(f'{state["title"]}.mp3', audio_path)
            path = audio_path / audio_name
            await ytb.send(MessageSegment.record(path))
            await upload_both(bot=bot, event=event, file_path=str(path.absolute()), name=audio_name)
    except Exception as e:
        await ytb.send(f"下载失败 | {e}")
    