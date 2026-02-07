import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

import aiofiles
from httpx import HTTPError, AsyncClient
from nonebot import logger
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
)

from .task import auto_task
from ..utils import merge_av, safe_unlink, generate_file_name
from ..config import pconfig
from ..constants import COMMON_HEADER, DOWNLOAD_TIMEOUT
from ..exception import DownloadException, ZeroSizeException, SizeLimitException


class StreamDownloader:
    """Downloader class for downloading files with stream"""

    def __init__(self):
        self.headers: dict[str, str] = COMMON_HEADER.copy()
        self.cache_dir: Path = pconfig.cache_dir
        self.client: AsyncClient = AsyncClient(timeout=DOWNLOAD_TIMEOUT, verify=False)
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
        )
        self._active_downloads = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def create_progress_task(self, desc: str, total: int | None = None):
        """progress task context manager"""
        async with self._lock:
            if self._active_downloads == 0:
                self.progress.start()
            self._active_downloads += 1

        task_id = self.progress.add_task(description=desc, total=total)
        try:
            yield lambda advance: self.progress.update(task_id, advance=advance)
        finally:
            async with self._lock:
                self.progress.remove_task(task_id)
                self._active_downloads -= 1
                if self._active_downloads == 0:
                    self.progress.stop()

    @auto_task
    async def streamd(
        self,
        url: str,
        *,
        file_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download file by url with stream"""
        if not file_name:
            file_name = generate_file_name(url)
        file_path = self.cache_dir / file_name
        # 如果文件存在，则直接返回
        if file_path.exists():
            return file_path

        headers = {**self.headers, **(ext_headers or {})}

        try:
            async with self.client.stream("GET", url, headers=headers, follow_redirects=True) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                content_length = int(content_length) if content_length else 0

                if content_length == 0:
                    logger.warning(f"媒体 url: {url}, 大小为 0, 取消下载")
                    raise ZeroSizeException

                if (file_size := content_length / 1024 / 1024) > pconfig.max_size:
                    logger.warning(f"媒体 url: {url} 大小 {file_size:.2f} MB 超过 {pconfig.max_size} MB, 取消下载")
                    raise SizeLimitException

                async with self.create_progress_task(file_name, content_length) as update_progress:
                    async with aiofiles.open(file_path, "wb") as file:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            await file.write(chunk)
                            update_progress(len(chunk))

        except HTTPError:
            await safe_unlink(file_path)
            logger.exception(f"下载失败 | url: {url}, file_path: {file_path}")
            raise DownloadException("媒体下载失败")

        return file_path

    @auto_task
    async def download_video(
        self,
        url: str,
        *,
        video_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download video file by url with stream"""
        if video_name is None:
            video_name = generate_file_name(url, ".mp4")
        return await self.streamd(url, file_name=video_name, ext_headers=ext_headers)

    @auto_task
    async def download_audio(
        self,
        url: str,
        *,
        audio_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download audio file by url with stream"""
        if audio_name is None:
            audio_name = generate_file_name(url, ".mp3")
        return await self.streamd(url, file_name=audio_name, ext_headers=ext_headers)

    @auto_task
    async def download_img(
        self,
        url: str,
        *,
        img_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download image file by url with stream"""
        if img_name is None:
            img_name = generate_file_name(url, ".jpg")
        return await self.streamd(url, file_name=img_name, ext_headers=ext_headers)

    @auto_task
    async def download_av_and_merge(
        self,
        v_url: str,
        a_url: str,
        *,
        output_path: Path,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download video and audio file by url with stream and merge"""
        v_path, a_path = await asyncio.gather(
            self.download_video(v_url, ext_headers=ext_headers),
            self.download_audio(a_url, ext_headers=ext_headers),
        )
        await merge_av(v_path=v_path, a_path=a_path, output_path=output_path)
        return output_path

    async def download_imgs_without_raise(
        self,
        urls: list[str],
        *,
        ext_headers: dict[str, str] | None = None,
    ) -> list[Path]:
        """download image files by urls with stream, ignore errors"""
        paths_or_errs = await asyncio.gather(
            *[self.download_img(url, ext_headers=ext_headers) for url in urls],
            return_exceptions=True,
        )
        return [p for p in paths_or_errs if isinstance(p, Path)]


DOWNLOADER: StreamDownloader = StreamDownloader()

try:
    import yt_dlp as yt_dlp

    from .ytdlp import YtdlpDownloader

    YTDLP_DOWNLOADER = YtdlpDownloader()
except ImportError:
    YTDLP_DOWNLOADER = None
