import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

from ..config import PROXY, plugin_cache_dir
from ..exception import ParseException
from ..utils import LimitedSizeDict, generate_file_name


class YtdlpDownloader:
    """YtdlpDownloader class"""

    def __init__(self):
        self._url_info_mapping = LimitedSizeDict[str, dict[str, str]]()
        self._ydl_extract_base_opts: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "force_generic_extractor": True,
        }
        self._ydl_download_base_opts: dict[str, Any] = {}
        if PROXY is not None:
            self._ydl_download_base_opts["proxy"] = PROXY
            self._ydl_extract_base_opts["proxy"] = PROXY

    async def extract_video_info(self, url: str, cookiefile: Path | None = None) -> dict[str, str]:
        """get video info by url

        Args:
            url (str): url address
            cookiefile (Path | None, optional): cookie file path. Defaults to None.

        Returns:
            dict[str, str]: video info
        """
        info_dict = self._url_info_mapping.get(url, None)
        if info_dict:
            return info_dict
        ydl_opts = {} | self._ydl_extract_base_opts

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
            if not info_dict:
                raise ParseException("获取视频信息失败")
            self._url_info_mapping[url] = info_dict
            return info_dict

    async def download_video(self, url: str, cookiefile: Path | None = None) -> Path:
        """download video by yt-dlp

        Args:
            url (str): url address
            cookiefile (Path | None, optional): cookie file path. Defaults to None.

        Returns:
            Path: video file path
        """
        info_dict = await self.extract_video_info(url, cookiefile)
        duration = int(info_dict.get("duration", 600))
        video_path = plugin_cache_dir / generate_file_name(url, ".mp4")
        if video_path.exists():
            return video_path
        ydl_opts = {
            "outtmpl": f"{video_path}",
            "merge_output_format": "mp4",
            "format": f"bv[filesize<={duration // 10 + 10}M]+ba/b[filesize<={duration // 8 + 10}M]",
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        } | self._ydl_download_base_opts

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        return video_path

    async def download_audio(self, url: str, cookiefile: Path | None = None) -> Path:
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
        } | self._ydl_download_base_opts

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        return audio_path
