import yt_dlp
import random
import asyncio

from nonebot import logger, require
from pathlib import Path
from ..config import video_path, audio_path, PROXY

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 缓存链接信息
url_info: dict[str, dict[str, str]] = {}

# 定时清理
@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=0,
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
    ydl_opts = {} | ydl_extract_base_opts

    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
        url_info[url] = info_dict
        return info_dict

        
async def ytdlp_download_video(url: str, cookiefile: Path = None) -> str:
    info_dict = url_info[url]
    if not info_dict:
        info_dict = await get_video_info(url, cookiefile)
    title = info_dict.get('title', random.randint(0, 1000))
    duration = info_dict.get('duration', 600)
    ydl_opts = {
        'outtmpl': f'{video_path / title}.%(ext)s',
        'merge_output_format': 'mp4',
        'format': f'best[filesize<{duration // 12}]'
    } | ydl_download_base_opts
    
    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return f'{title}.mp4'
        

async def ytdlp_download_audio(url: str, cookiefile: Path = None) -> str:
    info_dict = url_info[url]
    if not info_dict:
        info_dict = await get_video_info(url, cookiefile)
    title = info_dict.get('title', random.randint(0, 1000))
    # duration = info_dict.get('duration', 600)
    ydl_opts = {
        'outtmpl': f'{ audio_path / title}.%(ext)s',
        'format': 'bestaudio',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '0', }]
    } | ydl_download_base_opts
    
    if cookiefile:
        ydl_opts['cookiefile'] = str(cookiefile)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return f'{title}.mp3'