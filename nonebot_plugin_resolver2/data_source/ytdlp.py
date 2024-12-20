import asyncio
import importlib

from pathlib import Path
from nonebot import get_bot, get_driver, logger

from .common import delete_boring_characters
from ..config import *

# 缓存链接信息
url_info: dict[str, dict[str, str]] = {}

# 定时清理
@scheduler.scheduled_job(
    "cron",
    hour=2,
    minute=0,
)
async def _():
    url_info.clear()
    info = await update_yt_dlp()
    try:
        bot = get_bot()
        superuser_id: int = int(next(iter(get_driver().config.superusers), None))
        await bot.send_private_msg(user_id = superusers, message = info)
    except Exception:
        pass

async def update_yt_dlp() -> str:
    import yt_dlp
    import subprocess
    import pkg_resources
    process = await asyncio.create_subprocess_exec(
        'pip', 'install', '--upgrade', 'yt-dlp',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        try:
            importlib.reload(yt_dlp)
            version = pkg_resources.get_distribution('yt-dlp').version
            success_info = f"Successfully updated yt-dlp, current version: {version}"
            logger.info(success_info)
            return success_info
        except pkg_resources.DistributionNotFound:
            return "yt-dlp is not installed"
    else:
        err_info = f"Failed to update yt-dlp: {stderr.decode()}"
        logger.warning(err_info)
        return err_info
    
    
# 获取视频信息的 基础 opts
ydl_extract_base_opts = {
    'quiet': True,
    'skip_download': True,
    'force_generic_extractor': True
}

# 下载视频的 基础 opts
ydl_download_base_opts = {

}

if PROXY:
    ydl_download_base_opts['proxy'] = PROXY
    ydl_extract_base_opts['proxy'] = PROXY


async def get_video_info(url: str, cookiefile: Path = None) -> dict[str, str]:
    import yt_dlp
    info_dict = url_info.get(url, None)
    if info_dict: 
        return info_dict
    ydl_opts = {} | ydl_extract_base_opts

    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
        url_info[url] = info_dict
        return info_dict

        
async def ytdlp_download_video(url: str, cookiefile: Path = None) -> str:
    import yt_dlp
    info_dict = await get_video_info(url, cookiefile)
    title = delete_boring_characters(info_dict.get('title', 'titleless')[:50])
    duration = info_dict.get('duration', 600)
    ydl_opts = {
        'outtmpl': f'{plugin_cache_dir / title}.%(ext)s',
        'merge_output_format': 'mp4',
        'format': f'bv[filesize<={duration // 10 + 10}M]+ba/b[filesize<={duration // 8 + 10}M]',
        'postprocessors': [{ 'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
    } | ydl_download_base_opts
    
    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return f'{title}.mp4'
        

async def ytdlp_download_audio(url: str, cookiefile: Path = None) -> str:
    import yt_dlp
    info_dict = await get_video_info(url, cookiefile)
    title = delete_boring_characters(info_dict.get('title', 'titleless')[:50])
    ydl_opts = {
        'outtmpl': f'{ plugin_cache_dir / title}.%(ext)s',
        'format': 'bestaudio',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '0', }]
    } | ydl_download_base_opts
    
    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return f'{title}.mp3'
    
    