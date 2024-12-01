import yt_dlp
import random
import asyncio

from nonebot import logger
from pathlib import Path
from ..config import video_path, audio_path


async def get_video_title(url: str, cookiefile: str | Path = '', proxy: str = '') -> str:
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': True,
    }
    if proxy:
        ydl_opts['proxy'] = proxy
    if cookiefile:
        ydl_opts['cookiefile'] = cookiefile.absolute() if isinstance(cookiefile, Path) else cookiefile

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info
        info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
        return info_dict.get('title', '')
        
async def ytdlp_download_video(url: str, type: str, height: int = 1080, cookiefile: str | Path = '', proxy: str = '') -> str:
    filename = video_path / f"{type}-{random.randint(1, 10000)}"
    ydl_opts = {
        'outtmpl': f'{filename.cwd()}.%(ext)s',
        'merge_output_format': 'mp4',
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
    if cookiefile:
        ydl_opts['cookiefile'] = cookiefile.absolute() if isinstance(cookiefile, Path) else cookiefile

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return f'{filename}.mp4'
        

async def ytdlp_download_audio(url: str, type: str, cookiefile: str | Path = '', proxy: str = '') -> str:
    filename = audio_path / f"{type}-{random.randint(1, 10000)}"
    ydl_opts = {
        'outtmpl': f'{filename.cwd()}.%(ext)s',
        'format': 'bestaudio',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac', 'preferredquality': '0', }]
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
    if cookiefile:
        ydl_opts['cookiefile'] = cookiefile.absolute() if isinstance(cookiefile, Path) else cookiefile
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return f'{filename}.flac'