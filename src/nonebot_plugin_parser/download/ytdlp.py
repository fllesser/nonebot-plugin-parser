import asyncio
from typing import TYPE_CHECKING
from pathlib import Path

import yt_dlp
from msgspec import Struct, convert

from .task import auto_task
from ..utils import LimitedSizeDict, generate_file_name
from ..config import pconfig
from ..exception import ParseException, DurationLimitException


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
        if TYPE_CHECKING:
            from yt_dlp import _Params

        self._video_info_mapping = LimitedSizeDict[str, VideoInfo]()
        self._extract_base_opts: _Params = {
            "quiet": True,
            "skip_download": "1",
            "force_generic_extractor": True,
        }
        self._download_base_opts: _Params = {}
        if proxy := pconfig.proxy:
            self._download_base_opts["proxy"] = proxy
            self._extract_base_opts["proxy"] = proxy

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
        ydl_opts = self._extract_base_opts.copy()

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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

        ydl_opts = self._download_base_opts.copy()
        ydl_opts["outtmpl"] = str(video_path)
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["format"] = f"bv[filesize<={duration // 10 + 10}M]+ba/b[filesize<={duration // 8 + 10}M]"
        ydl_opts["postprocessors"] = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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

        ydl_opts = self._download_base_opts.copy()
        ydl_opts["outtmpl"] = f"{pconfig.cache_dir / file_name}.%(ext)s"
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac",
                "preferredquality": "0",
            }
        ]

        if cookiefile:
            ydl_opts["cookiefile"] = str(cookiefile)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        return audio_path
