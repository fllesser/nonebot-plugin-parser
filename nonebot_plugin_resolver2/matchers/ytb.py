from pathlib import Path
import re

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.params import Arg
from nonebot.plugin.on import on_keyword
from nonebot.rule import Rule
from nonebot.typing import T_State

from nonebot_plugin_resolver2.config import NEED_UPLOAD, NICKNAME, ytb_cookies_file
from nonebot_plugin_resolver2.download.utils import keep_zh_en_num
from nonebot_plugin_resolver2.download.ytdlp import get_video_info, ytdlp_download_audio, ytdlp_download_video

from .filter import is_not_in_disabled_groups
from .utils import get_file_seg, get_video_seg

ytb = on_keyword(keywords={"youtube.com", "youtu.be"}, rule=Rule(is_not_in_disabled_groups))


@ytb.handle()
async def _(event: MessageEvent, state: T_State):
    message = event.message.extract_plain_text().strip()
    pattern = (
        # https://youtu.be/EKkzbbLYPuI?si=K_S9zIp5g7DhigVz
        # https://www.youtube.com/watch?v=1LnPnmKALL8&list=RD8AxpdwegNKc&index=2
        r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[A-Za-z\d\._\?%&\+\-=/#]+"
    )
    if match := re.search(pattern, message):
        url = match.group(0)
    else:
        logger.warning(f"{message} 中的链接不支持，已忽略")
        await ytb.finish()
    try:
        info_dict = await get_video_info(url, ytb_cookies_file)
        title = info_dict.get("title", "未知")
        await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")
    except Exception as e:
        await ytb.finish(f"{NICKNAME}解析 | 油管 - 标题获取出错: {e}")
    state["url"] = url
    state["title"] = title


@ytb.got("type", prompt="您需要下载音频(0)，还是视频(1)")
async def _(bot: Bot, event: MessageEvent, state: T_State, type: Message = Arg()):
    url: str = state["url"]
    title: str = state["title"]
    await bot.call_api("set_msg_emoji_like", message_id=event.message_id, emoji_id="282")
    video_path: Path | None = None
    audio_path: Path | None = None
    is_video = type.extract_plain_text().strip() == "1"
    try:
        if is_video:
            video_path = await ytdlp_download_video(url, ytb_cookies_file)
        else:
            audio_path = await ytdlp_download_audio(url, ytb_cookies_file)
    except Exception as e:
        media_type = "视频" if is_video else "音频"
        logger.error(f"{media_type}下载失败 | {url} | {e}", exc_info=True)
        await ytb.send(f"{media_type}下载失败, 请联系机器人管理员", reply_message=True)
    if video_path:
        await ytb.send(await get_video_seg(video_path))
    elif audio_path:
        await ytb.send(MessageSegment.record(audio_path))
        if NEED_UPLOAD:
            file_name = f"{keep_zh_en_num(title)}.flac"
            await ytb.send(get_file_seg(audio_path, file_name))
