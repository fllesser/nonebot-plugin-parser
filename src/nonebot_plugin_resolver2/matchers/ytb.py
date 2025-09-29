from pathlib import Path
import re
from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import PausePromptResult
from nonebot.typing import T_State
from nonebot_plugin_alconna.uniseg import UniMessage

from ..config import NEED_UPLOAD, NICKNAME, ytb_cookies_file
from ..download.ytdlp import get_video_info, ytdlp_download_audio, ytdlp_download_video
from ..exception import handle_exception
from ..utils import keep_zh_en_num
from .helper import UniHelper
from .preprocess import KeyPatternMatched, on_keyword_regex

# https://youtu.be/EKkzbbLYPuI?si=K_S9zIp5g7DhigVz
# https://www.youtube.com/watch?v=1LnPnmKALL8&list=RD8AxpdwegNKc&index=2
ytb = on_keyword_regex(
    ("youtube.com", r"https?://(?:www\.)?youtube\.com/[A-Za-z\d\._\?%&\+\-=/#]+"),
    ("youtu.be", r"https?://(?:www\.)?youtu\.be/[A-Za-z\d\._\?%&\+\-=/#]+"),
)


@ytb.handle()
@handle_exception()
async def _(state: T_State, searched: re.Match[str] = KeyPatternMatched()):
    url = searched.group(0)
    try:
        info_dict = await get_video_info(url, ytb_cookies_file)
        title = info_dict.get("title", "未知")
    except Exception:
        logger.exception(f"油管标题获取失败 | {url}")
        await ytb.finish(f"{NICKNAME}解析 | 油管 - 标题获取出错")
    await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")
    state["url"] = url
    state["title"] = title
    await ytb.pause("您需要下载音频(0)，还是视频(1)")


@ytb.handle()
async def _(
    bot: Bot,
    event: MessageEvent,
    state: T_State,
    pause_result: Any = PausePromptResult(),
):
    # 回应用户
    await bot.call_api("set_msg_emoji_like", message_id=event.message_id, emoji_id="282")
    # 撤回 选择类型 的 prompt
    await bot.delete_msg(message_id=pause_result["message_id"])
    # 获取 url 和 title
    url: str = state["url"]
    title: str = state["title"]
    # 下载视频或音频
    video_path: Path | None = None
    audio_path: Path | None = None
    # 判断是否下载视频
    type = event.message.extract_plain_text().strip()
    is_video = type == "1"
    try:
        if is_video:
            video_path = await ytdlp_download_video(url, ytb_cookies_file)
        else:
            audio_path = await ytdlp_download_audio(url, ytb_cookies_file)
    except Exception:
        media_type = "视频" if is_video else "音频"
        logger.exception(f"{media_type}下载失败 | {url}")
        await ytb.finish(f"{media_type}下载失败", reply_message=True)
    # 发送视频或音频
    if video_path:
        await UniMessage([UniHelper.video_seg(video_path)]).send()
    elif audio_path:
        await UniMessage([UniHelper.record_seg(audio_path)]).send()
        if NEED_UPLOAD:
            file_name = f"{keep_zh_en_num(title)}.flac"
            await UniMessage([UniHelper.file_seg(audio_path, display_name=file_name)]).send()
