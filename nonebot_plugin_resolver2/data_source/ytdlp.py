import asyncio
import yt_dlp

from pathlib import Path
from nonebot import get_bot, get_driver
from nonebot.log import logger

from .common import delete_boring_characters
from ..config import (
    plugin_cache_dir,
    scheduler,
    PROXY
)

# 缓存链接信息
url_info: dict[str, dict[str, str]] = {}

# 定时清理
@scheduler.scheduled_job(
    "cron",
    hour=2,
    minute=0,
    id = "resolver2-clean-url-info"
)
async def _():
    url_info.clear()
    
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

        
async def ytdlp_download_video(url: str, cookiefile: Path = None) -> Path:
    info_dict = await get_video_info(url, cookiefile)
    title = delete_boring_characters(info_dict.get('title', 'titleless')[:50])
    duration = info_dict.get('duration', 600)
    video_path = plugin_cache_dir / f'{title}.mp4'
    if video_path.exists():
        return video_path
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
    return video_path
        

async def ytdlp_download_audio(url: str, cookiefile: Path = None) -> Path:
    info_dict = await get_video_info(url, cookiefile)
    title = delete_boring_characters(info_dict.get('title', 'titleless')[:50])
    audio_path = plugin_cache_dir / f'{title}.flac'
    if audio_path.exists():
        return audio_path
    ydl_opts = {
        'outtmpl': f'{plugin_cache_dir / title}.%(ext)s',
        'format': 'bestaudio',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac', 'preferredquality': '0', }]
    } | ydl_download_base_opts
    
    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return audio_path
    
    