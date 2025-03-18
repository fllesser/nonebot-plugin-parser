import asyncio
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yt_dlp

from nonebot_plugin_resolver2.config import PROXY, plugin_cache_dir

from .utils import generate_file_name


# 使用定长字典缓存链接信息，最多保存 20 个条目
class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, max_size=20, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            self.popitem(last=False)  # 移除最早添加的项


# 使用定长字典缓存链接信息，最多保存 20 个条目
url_info_mapping: LimitedSizeDict = LimitedSizeDict()

# 获取视频信息的 基础 opts
ydl_extract_base_opts: dict[str, Any] = {
    "quiet": True,
    "skip_download": True,
    "force_generic_extractor": True,
}

# 下载视频的 基础 opts
ydl_download_base_opts: dict[str, Any] = {}

if PROXY is not None:
    ydl_download_base_opts["proxy"] = PROXY
    ydl_extract_base_opts["proxy"] = PROXY


async def get_video_info(url: str, cookiefile: Path | None = None) -> dict[str, str]:
    """get video info by url

    Args:
        url (str): url address
        cookiefile (Path | None, optional): cookie file path. Defaults to None.

    Returns:
        dict[str, str]: video info
    """
    info_dict = url_info_mapping.get(url, None)
    if info_dict:
        return info_dict
    ydl_opts = {} | ydl_extract_base_opts

    if cookiefile:
        ydl_opts["cookiefile"] = str(cookiefile)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
        assert info_dict, "获取视频信息失败"
        url_info_mapping[url] = info_dict
        return info_dict


async def ytdlp_download_video(url: str, cookiefile: Path | None = None) -> Path:
    """download video by yt-dlp

    Args:
        url (str): url address
        cookiefile (Path | None, optional): cookie file path. Defaults to None.

    Returns:
        Path: video file path
    """
    info_dict = await get_video_info(url, cookiefile)
    duration = int(info_dict.get("duration", 600))
    video_path = plugin_cache_dir / generate_file_name(url, ".mp4")
    if video_path.exists():
        return video_path
    ydl_opts = {
        "outtmpl": f"{video_path}",
        "merge_output_format": "mp4",
        "format": f"bv[filesize<={duration // 10 + 10}M]+ba/b[filesize<={duration // 8 + 10}M]",
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
    } | ydl_download_base_opts

    if cookiefile:
        ydl_opts["cookiefile"] = str(cookiefile)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return video_path


async def ytdlp_download_audio(url: str, cookiefile: Path | None = None) -> Path:
    """download audio by yt-dlp

    Args:
        url (str): url address
        cookiefile (Path | None, optional): cookie file path. Defaults to None.

    Returns:
        Path: audio file path
    """
    file_name = generate_file_name(url)
    audio_path = plugin_cache_dir / f"{file_name}.flac"
    if audio_path.exists():
        return audio_path
    ydl_opts = {
        "outtmpl": f"{plugin_cache_dir / file_name}.%(ext)s",
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac",
                "preferredquality": "0",
            }
        ],
    } | ydl_download_base_opts

    if cookiefile:
        ydl_opts["cookiefile"] = str(cookiefile)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return audio_path
