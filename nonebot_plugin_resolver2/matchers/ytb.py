import re

from nonebot.typing import T_State
from nonebot.params import Arg
from nonebot.rule import Rule
from nonebot.exception import ActionFailed
from nonebot.plugin.on import on_keyword
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment

from .filter import is_not_in_disable_group
from .utils import get_video_seg, get_file_seg
from ..download.ytdlp import get_video_info, ytdlp_download_audio, ytdlp_download_video
from ..config import (
    NICKNAME,
    ytb_cookies_file,
)

ytb = on_keyword(
    keywords={"youtube.com", "youtu.be"}, rule=Rule(is_not_in_disable_group)
)


@ytb.handle()
async def _(event: MessageEvent, state: T_State):
    message = event.message.extract_plain_text().strip()
    pattern = (
        r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[A-Za-z\d._?%&+\-=/#]*"
    )
    if match := re.search(pattern, message):
        url = match.group(0)
    else:
        await ytb.finish()
    try:
        info_dict = await get_video_info(url, ytb_cookies_file)
        title = info_dict.get("title", "未知")
        await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")
    except Exception as e:
        await ytb.finish(f"{NICKNAME}解析 | 油管 - 标题获取出错: {e}")
    state["url"] = url


@ytb.got("type", prompt="您需要下载音频(0)，还是视频(1)")
async def _(bot: Bot, event: MessageEvent, state: T_State, type: Message = Arg()):
    url: str = state["url"]
    await bot.call_api(
        "set_msg_emoji_like", message_id=event.message_id, emoji_id="282"
    )
    try:
        if type.extract_plain_text().strip() == "1":
            video_path = await ytdlp_download_video(
                url=url, cookiefile=ytb_cookies_file
            )
            await ytb.send(await get_video_seg(video_path))
        else:
            audio_path = await ytdlp_download_audio(
                url=url, cookiefile=ytb_cookies_file
            )
            await ytb.send(MessageSegment.record(audio_path))
            await ytb.send(get_file_seg(audio_path))
    except Exception as e:
        if not isinstance(e, ActionFailed):
            await ytb.send(f"下载失败 | {e}")
