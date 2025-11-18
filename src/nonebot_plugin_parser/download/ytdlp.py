import asyncio
from pathlib import Path
from typing import Any

from msgspec import Struct, convert
import yt_dlp

from ..config import pconfig
from ..exception import DurationLimitException, ParseException
from ..utils import LimitedSizeDict, generate_file_name
from .task import auto_task


class VideoInfo(Struct):
    title: str
    """标题"""
    channel: str
    """频道名称"""
    uploader: str
    """上传者 id"""
    duration: int
    """时长"""
    timestamp: int
    """发布时间戳"""
    thumbnail: str
    """封面图片"""
    description: str
    """简介"""
    channel_id: str
    """频道 id"""

    @property
    def author_name(self) -> str:
        return f"{self.channel}@{self.uploader}"


class YtdlpDownloader:
    """YtdlpDownloader class"""

    def __init__(self):
        self._video_info_mapping = LimitedSizeDict[str, VideoInfo]()
        self._ydl_extract_base_opts: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "force_generic_extractor": True,
        }
        self._ydl_download_base_opts: dict[str, Any] = {}
        if proxy := pconfig.proxy:
            self._ydl_download_base_opts["proxy"] = proxy
            self._ydl_extract_base_opts["proxy"] = proxy

    async def extract_video_info(self, url: str, cookiefile: Path | None = None) -> VideoInfo:
        """get video info by url

        Args:
            url (str): url address
            cookiefile (Path | None ): cookie file path. Defaults to None.

        Returns:
            dict[str, str]: video info
        """
        video_info = self._video_info_mapping.get(url, None)
        if video_info:
            return video_info
        ydl_opts = self._ydl_extract_base_opts.copy()

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
            info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
            if not info_dict:
                raise ParseException("获取视频信息失败")

        video_info = convert(info_dict, VideoInfo)
        self._video_info_mapping[url] = video_info
        return video_info

    @auto_task
    async def download_video(self, url: str, cookiefile: Path | None = None) -> Path:
        """download video by yt-dlp

        Args:
            url (str): url address
            cookiefile (Path | None): cookie file path. Defaults to None.

        Returns:
            Path: video file path
        """
        video_info = await self.extract_video_info(url, cookiefile)
        duration = video_info.duration
        if duration > pconfig.duration_maximum:
            raise DurationLimitException

        video_path = pconfig.cache_dir / generate_file_name(url, ".mp4")
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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
            await asyncio.to_thread(ydl.download, [url])
        return video_path

    @auto_task
    async def download_audio(self, url: str, cookiefile: Path | None = None) -> Path:
        """download audio by yt-dlp

        Args:
            url (str): url address
            cookiefile (Path | None): cookie file path. Defaults to None.

        Returns:
            Path: audio file path
        """
        file_name = generate_file_name(url)
        audio_path = pconfig.cache_dir / f"{file_name}.flac"
        if audio_path.exists():
            return audio_path

        ydl_opts = {
            "outtmpl": f"{pconfig.cache_dir / file_name}.%(ext)s",
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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
            await asyncio.to_thread(ydl.download, [url])
        return audio_path
