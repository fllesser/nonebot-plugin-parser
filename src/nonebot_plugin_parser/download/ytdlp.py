import asyncio
from typing import TYPE_CHECKING
from pathlib import Path
from collections import defaultdict

import yt_dlp
from msgspec import Struct, convert
from nonebot import logger

from .task import auto_task
from ..utils import LimitedSizeDict, generate_file_name
from ..config import pconfig
from ..exception import ParseException, IgnoreException


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
        self._url_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        if proxy := pconfig.proxy:
            self._download_base_opts["proxy"] = proxy
            self._extract_base_opts["proxy"] = proxy

    @staticmethod
    def _coerce_info_dict(info_dict: dict) -> dict:
        data = dict(info_dict)
        duration = data.get("duration")
        if isinstance(duration, float):
            data["duration"] = int(duration)
        elif data.get("duration") is None:
            data["duration"] = 0
        timestamp = data.get("timestamp")
        if isinstance(timestamp, float):
            data["timestamp"] = int(timestamp)
        elif data.get("timestamp") is None:
            data["timestamp"] = 0
        channel = (data.get("channel") or data.get("uploader") or "").strip()
        uploader = (data.get("uploader") or channel or "unknown").strip()
        data["channel"] = channel
        data["uploader"] = uploader
        data["channel_id"] = str(data.get("channel_id") or data.get("uploader_id") or uploader)
        data["title"] = (data.get("title") or "").strip()
        data["thumbnail"] = data.get("thumbnail") or ""
        data["description"] = (data.get("description") or "").strip()
        return data

    async def extract_video_info(self, url: str, cookiefile: Path | None = None) -> VideoInfo:
        """Get video info by yt-dlp"""

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

        info_dict = self._coerce_info_dict(info_dict)
        video_info = convert(info_dict, VideoInfo)
        self._video_info_mapping[url] = video_info
        return video_info

    @auto_task
    async def download_video(self, url: str, cookiefile: Path | None = None) -> Path:
        """Download video by yt-dlp"""

        video_info = await self.extract_video_info(url, cookiefile)
        duration = video_info.duration
        if duration > pconfig.duration_maximum:
            logger.warning(f"视频时长 {duration} 秒, 超过 {pconfig.duration_maximum} 秒, 取消下载")
            raise IgnoreException

        video_path = pconfig.cache_dir / generate_file_name(url, ".mp4")
        if video_path.exists():
            return video_path

        async with self._url_locks[url]:
            if video_path.exists():
                return video_path

            pconfig.cache_dir.mkdir(parents=True, exist_ok=True)

            ydl_opts = self._download_base_opts.copy()
            ydl_opts["outtmpl"] = str(video_path)
            ydl_opts["merge_output_format"] = "mp4"
            ydl_opts["postprocessors"] = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]

            if cookiefile:
                ydl_opts["cookiefile"] = str(cookiefile)

            # Instagram 等站点格式常无 filesize，严格 filesize 过滤会报 Requested format is not available
            format_strict = (
                f"bv[filesize<={duration // 10 + 10}M]+ba/b[filesize<={duration // 8 + 10}M]"
            )
            format_fallback = "bestvideo*+bestaudio/best[ext=mp4]/best"

            async def _run_download(fmt: str) -> None:
                opts = ydl_opts.copy()
                opts["format"] = fmt
                with yt_dlp.YoutubeDL(opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])

            try:
                try:
                    await _run_download(format_strict)
                except Exception as first_exc:
                    if video_path.exists():
                        return video_path
                    msg = str(first_exc).lower()
                    if "requested format is not available" in msg or "format is not available" in msg:
                        logger.warning(
                            f"yt-dlp 严格格式不可用，回退通用格式 | url={url}"
                        )
                        await _run_download(format_fallback)
                    else:
                        raise
            except Exception:
                if video_path.exists():
                    return video_path
                raise
        return video_path

    @auto_task
    async def download_audio(self, url: str, cookiefile: Path | None = None) -> Path:
        """Download audio by yt-dlp"""

        file_name = generate_file_name(url)
        audio_path = pconfig.cache_dir / f"{file_name}.flac"
        if audio_path.exists():
            return audio_path

        async with self._url_locks[url]:
            if audio_path.exists():
                return audio_path

            pconfig.cache_dir.mkdir(parents=True, exist_ok=True)

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
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])
            except Exception:
                if audio_path.exists():
                    return audio_path
                raise
        return audio_path
