import re
import asyncio

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.params import Arg
from nonebot.rule import Rule
from nonebot.exception import ActionFailed
from nonebot.permission import SUPERUSER
from nonebot.plugin.on import on_keyword, on_command
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    Message,
    MessageSegment,
    Bot
)

from .filter import is_not_in_disable_group
from .utils import get_video_seg, get_file_seg
from ..download.ytdlp import (
    get_video_info,
    ytdlp_download_audio,
    ytdlp_download_video
)
from ..config import (
    NICKNAME,
    ytb_cookies_file,
    scheduler
)

ytb = on_keyword(
    keywords = {"youtube.com", "youtu.be"},
    rule = Rule(is_not_in_disable_group)
)

# update_yt = on_command(
#     cmd="update yt", 
#     permission=SUPERUSER
# )

@ytb.handle()
async def _(event: MessageEvent, state: T_State):
    message = event.message.extract_plain_text().strip()
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[A-Za-z\d._?%&+\-=/#]*"
    if match := re.search(pattern, message):
        url = match.group(0)
    else:
        await ytb.finish()
    try:
        info_dict = await get_video_info(url, ytb_cookies_file)
        title = info_dict.get('title', "未知")
        await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")
    except Exception as e:
        await ytb.finish(f"{NICKNAME}解析 | 油管 - 标题获取出错: {e}")
    state["url"] = url

@ytb.got("type", prompt="您需要下载音频(0)，还是视频(1)")
async def _(bot: Bot, event: MessageEvent, state: T_State, type: Message = Arg()):
    url: str = state["url"]
    await bot.call_api("set_msg_emoji_like", message_id = event.message_id, emoji_id = '282')
    try:
        if type.extract_plain_text().strip() == '1':
            video_path = await ytdlp_download_video(url = url, cookiefile = ytb_cookies_file)
            await ytb.send(await get_video_seg(video_path))
        else: 
            audio_path = await ytdlp_download_audio(url = url, cookiefile = ytb_cookies_file)
            await ytb.send(MessageSegment.record(audio_path))
            await ytb.send(get_file_seg(audio_path))
    except Exception as e:
        if not isinstance(e, ActionFailed):
            await ytb.send(f"下载失败 | {e}")
        
# @update_yt.handle()
# async def _(event: MessageEvent):
#     get_video_info, ytdlp_download_video, ytdlp_download_audio = await update_ytdlp()
#     version = await get_yt_dlp_version()
#     await update_yt.finish(f"Successfully updated {version}")

# @scheduler.scheduled_job(
#     "cron",
#     hour=3,
#     minute=0,
# )
# async def _():
#     get_video_info, ytdlp_download_video, ytdlp_download_audio = await update_ytdlp()
#     version = await get_yt_dlp_version()
#     success_info = f"Successfully updated {version}"
#     try:
#         bot = get_bot()
#         if superuser_id := int(next(iter(get_driver().config.superusers), None)):
#             await bot.send_private_msg(user_id = superuser_id, message = success_info)
#     except Exception:
#         pass
        

# async def update_ytdlp() -> str:
#     import subprocess
#     import importlib
#     import sys
#     process = await asyncio.create_subprocess_exec(
#         'pip', 'install', '--upgrade', 'yt-dlp',
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE
#     )
#     stdout, stderr = await process.communicate()
#     if process.returncode == 0:
#         if 'yt_dlp' in sys.modules:
#             del sys.modules['yt_dlp']
#             logger.warning('delete cache of yt_dlp')
#         import yt_dlp
#         if 'nonebot_plugin_resolver2.download.ytdlp' in sys.modules:
#             del sys.modules['nonebot_plugin_resolver2.download.ytdlp']
#             logger.warning('delete cache of nonebot_plugin_resolver2.download.ytdlp')
#         from ..download import ytdlp
#         importlib.reload(yt_dlp)
#         importlib.reload(ytdlp)
#         from ..download.ytdlp import (
#             get_video_info,
#             ytdlp_download_audio,
#             ytdlp_download_video
#         )
#         return get_video_info, ytdlp_download_audio, ytdlp_download_video
#     else:
#         logger.error(f"Failed to update yt-dlp: {stderr.decode()}")
        
# async def get_yt_dlp_version():
#     import subprocess
#     process = await asyncio.create_subprocess_exec(
#         'yt-dlp', '--version',
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE
#     )
#     stdout, stderr = await process.communicate()
#     if process.returncode == 0:
#         version = stdout.decode().strip()
#         return f"yt-dlp {version}"
#     else:
#         error_message = stderr.decode().strip()
#         return f"Failed to get yt-dlp version: {error_message}"
