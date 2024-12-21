import re
import asyncio

from nonebot import on_keyword, on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment, Bot
from nonebot.typing import T_State
from nonebot.params import Arg
from nonebot.rule import Rule
from nonebot.exception import ActionFailed
from nonebot.permission import SUPERUSER

from .filter import is_not_in_disable_group
from .utils import get_video_seg, get_file_seg
from ..data_source.ytdlp import (
    get_video_info,
    ytdlp_download_audio,
    ytdlp_download_video
    )
from ..config import *

ytb = on_keyword(keywords = {"youtube.com", "youtu.be"}, rule = Rule(is_not_in_disable_group))
update_yt = on_command(cmd="update yt", permission=SUPERUSER)

@ytb.handle()
async def _(event: MessageEvent, state: T_State):
    message = event.message.extract_plain_text().strip()
    pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/[A-Za-z\d._?%&+\-=/#]*"
    if match := re.search(pattern, message):
        url = match.group(0)
    else:
        return
    try:
        info_dict = await get_video_info(url, YTB_COOKIES_FILE)
        title = info_dict.get('title', "未知")
        await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")
    except Exception as e:
        await ytb.finish(f"{NICKNAME}解析 | 油管 - 标题获取出错: {e}")
    state["url"] = url

@ytb.got("type", prompt="您需要下载音频(0)，还是视频(1)")
async def _(bot: Bot, event: MessageEvent, state: T_State, type: Message = Arg()):
    url: str = state["url"]
    # will_delete_id = (await ytb.send("下载中......"))["message_id"]
    await bot.call_api("set_msg_emoji_like", message_id = event.message_id, emoji_id = '282')
    try:
        if type.extract_plain_text().strip() == '1':
            video_name = await ytdlp_download_video(url = url, cookiefile = YTB_COOKIES_FILE)
            await ytb.send(await get_video_seg(video_name))
        else: 
            audio_name = await ytdlp_download_audio(url = url, cookiefile = YTB_COOKIES_FILE)
            await ytb.send(MessageSegment.record(plugin_cache_dir / audio_name))
            await ytb.send(get_file_seg(audio_name))
    except Exception as e:
        if not isinstance(e, ActionFailed):
            await ytb.send(f"下载失败 | {e}")
    # finally:
        # await bot.delete_msg(message_id = will_delete_id)
        
        
@update_yt.handle()
async def _(event: MessageEvent):
    get_video_info, ytdlp_download_video, ytdlp_download_audio = await update_ytdlp()
    version = await get_yt_dlp_version()
    success_info = f"Successfully updated {version}"
    await update_yt.finish()

@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=0,
)
async def _():
    get_video_info, ytdlp_download_video, ytdlp_download_audio = await update_ytdlp()
    version = await get_yt_dlp_version()
    success_info = f"Successfully updated {version}"
    try:
        bot = get_bot()
        superuser_id: int = int(next(iter(get_driver().config.superusers), None))
        await bot.send_private_msg(user_id = superuser_id, message = success_info )
    except Exception:
        pass

async def update_ytdlp() -> str:
    import subprocess
    import importlib
    import sys
    process = await asyncio.create_subprocess_exec(
        'pip', 'install', '--upgrade', 'yt-dlp',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        if 'yt_dlp' in sys.modules:
            del sys.modules['yt_dlp']
            logger.warning('delete cache of yt_dlp')
        import yt_dlp
        if 'nonebot_plugin_resolver2.data_source.ytdlp' in sys.modules:
            del sys.modules['nonebot_plugin_resolver2.data_source.ytdlp']
            logger.warning('delete cache of nonebot_plugin_resolver2.data_source.ytdlp')
        from ..data_source import ytdlp
        importlib.reload(yt_dlp)
        importlib.reload(ytdlp)
        from ..data_source.ytdlp import (
            get_video_info,
            ytdlp_download_audio,
            ytdlp_download_video
        )
        return get_video_info, ytdlp_download_audio, ytdlp_download_video
    else:
        logger.error(f"Failed to update yt-dlp: {stderr.decode()}")
        
async def get_yt_dlp_version():
    import subprocess
    process = await asyncio.create_subprocess_exec(
        'yt-dlp', '--version',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        version = stdout.decode().strip()
        return f"yt-dlp {version}"
    else:
        error_message = stderr.decode().strip()
        return f"Failed to get yt-dlp version: {error_message}"
