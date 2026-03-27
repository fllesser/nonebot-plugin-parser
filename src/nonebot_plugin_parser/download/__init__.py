import asyncio
from pathlib import Path
from functools import partial
from contextlib import contextmanager
from urllib.parse import urljoin

import httpx
import aiofiles
import curl_cffi
from nonebot import logger, get_driver
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    DownloadColumn,
)

from .task import auto_task
from ..utils import merge_av, safe_unlink, generate_file_name
from ..config import pconfig
from ..constants import COMMON_HEADER, DOWNLOAD_TIMEOUT
from ..exception import IgnoreException, DownloadException


class StreamDownloader:
    """Downloader class for downloading files with stream"""

    def __init__(self):
        self.headers: dict[str, str] = COMMON_HEADER.copy()
        self.cache_dir: Path = pconfig.cache_dir
        self.client: httpx.AsyncClient = httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, verify=False)

    async def aclose(self):
        """关闭 httpx client, 清理资源"""
        await self.client.aclose()

    @contextmanager
    def rich_progress(
        self,
        desc: str,
        total: int | None = None,
    ):
        with Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
        ) as progress:
            task_id = progress.add_task(description=desc, total=total)
            yield partial(progress.update, task_id)

    def _validate_content_length(
        self,
        response: httpx.Response | curl_cffi.Response,
    ) -> int:
        """获取文件长度"""
        content_length = response.headers.get("Content-Length")
        content_length = int(content_length) if content_length else 0

        if content_length == 0:
            logger.warning(f"媒体 url: {response.url}, 大小为 0, 取消下载")
            raise IgnoreException

        if (file_size := content_length / 1024 / 1024) > pconfig.max_size:
            logger.warning(f"媒体 url: {response.url} 大小 {file_size:.2f} MB, 超过 {pconfig.max_size} MB, 取消下载")
            raise IgnoreException

        return content_length

    async def _download_file_with_httpx(
        self,
        url: str,
        *,
        file_path: Path,
        headers: dict[str, str],
        chunk_size: int = 64 * 1024,
    ) -> Path:
        """download file by url with stream"""

        async with self.client.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=True,
        ) as response:
            response.raise_for_status()
            content_length = self._validate_content_length(response)

            with self.rich_progress(
                f"httpx | {file_path.name}",
                content_length,
            ) as update_progress:
                async with aiofiles.open(file_path, "wb") as file:
                    async for chunk in response.aiter_bytes(chunk_size):
                        await file.write(chunk)
                        update_progress(advance=len(chunk))

        return file_path

    async def _download_file_with_curl_cffi(
        self,
        url: str,
        *,
        file_path: Path,
        headers: dict[str, str],
    ) -> Path:
        async with curl_cffi.AsyncSession(allow_redirects=True) as session:
            response: curl_cffi.Response = await session.get(
                url,
                headers=headers,
                timeout=DOWNLOAD_TIMEOUT,
                stream=True,
            )
            response.raise_for_status()
            content_length = self._validate_content_length(response)

            with self.rich_progress(
                f"curl_cffi | {file_path.name}",
                content_length,
            ) as update_progress:
                async with aiofiles.open(file_path, "wb") as file:
                    async for chunk in response.aiter_content(chunk_size=8192):
                        await file.write(chunk)
                        update_progress(advance=len(chunk))

        return file_path

    async def _download_file(
        self,
        url: str,
        *,
        file_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
        chunk_size: int = 64 * 1024,
    ) -> Path:
        """download file by url with fallback"""
        if not file_name:
            file_name = generate_file_name(url)
        file_path = self.cache_dir / file_name
        if file_path.exists():
            return file_path

        headers = {**self.headers, **(ext_headers or {})}

        try:
            path = await self._download_file_with_httpx(
                url, file_path=file_path, headers=headers, chunk_size=chunk_size
            )
        except httpx.HTTPError:
            logger.opt(exception=True).warning(f"下载失败(httpx) | url: {url}")
            try:
                path = await self._download_file_with_curl_cffi(url, file_path=file_path, headers=headers)
            except curl_cffi.CurlError:
                logger.opt(exception=True).warning(f"下载失败(curl_cffi) | url: {url}")
                raise DownloadException("媒体下载失败")

        return path

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

        return await self._download_file(
            url,
            file_name=video_name,
            ext_headers=ext_headers,
            chunk_size=1024 * 1024,
        )

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

        return await self._download_file(
            url,
            file_name=audio_name,
            ext_headers=ext_headers,
        )

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

        return await self._download_file(
            url,
            file_name=img_name,
            ext_headers=ext_headers,
        )

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
            self._download_file(v_url, ext_headers=ext_headers),
            self._download_file(a_url, ext_headers=ext_headers),
        )
        await merge_av(v_path=v_path, a_path=a_path, output_path=output_path)
        return output_path

    @auto_task
    async def download_m3u8(
        self,
        m3u8_url: str,
        *,
        video_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download m3u8 file by url with stream"""
        if video_name is None:
            video_name = generate_file_name(m3u8_url, ".mp4")

        video_path = pconfig.cache_dir / video_name

        try:
            async with aiofiles.open(video_path, "wb") as f:
                total_size = 0
                with self.rich_progress(desc=video_name) as update_progress:
                    for url in await self._get_m3u8_slices(m3u8_url):
                        async with self.client.stream("GET", url, headers=ext_headers) as response:
                            async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                                await f.write(chunk)
                                total_size += len(chunk)
                                update_progress(advance=len(chunk), total=total_size)
        except httpx.HTTPError:
            await safe_unlink(video_path)
            logger.exception("m3u8 视频下载失败")
            raise DownloadException("m3u8 视频下载失败")

        return video_path

    async def _get_m3u8_slices(self, m3u8_url: str):
        """获取 m3u8 分片"""

        response = await self.client.get(m3u8_url)
        response.raise_for_status()

        slices_text = response.text
        slices: list[str] = []

        for line in slices_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            slices.append(urljoin(m3u8_url, line))

        return slices


downloader: StreamDownloader = StreamDownloader()
"""全局下载器实例，提供下载功能"""
yt_dlp_downloader = None
"""yt-dlp 下载器实例，提供下载视频功能，若 yt-dlp 未安装则为 None"""

from ..utils import is_module_available

if is_module_available("yt_dlp"):
    from .ytdlp import YtdlpDownloader

    yt_dlp_downloader = YtdlpDownloader()


@get_driver().on_shutdown
async def close_download_client():
    logger.debug("正在关闭下载器...")
    await downloader.aclose()
