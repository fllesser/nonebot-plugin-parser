import asyncio
from pathlib import Path

import aiofiles
import httpx
from nonebot import logger
from tqdm.asyncio import tqdm

from ..config import MAX_SIZE, plugin_cache_dir
from ..constants import COMMON_HEADER, DOWNLOAD_TIMEOUT
from ..exception import DownloadException
from ..utils import safe_unlink
from .utils import generate_file_name


class StreamDownloader:
    """Downloader class for downloading files with stream"""

    def __init__(self):
        # httpx.AsyncClient
        self.client = httpx.AsyncClient(
            timeout=DOWNLOAD_TIMEOUT,
            verify=False,
        )

    async def download_file_by_stream(
        self,
        url: str,
        *,
        file_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download file by url with stream

        Args:
            url (str): url address
            file_name (str | None, optional): file name. Defaults to get name by parse_url_resource_name.
            ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

        Returns:
            Path: file path

        Raises:
            httpx.HTTPError: When download fails
        """

        if not file_name:
            file_name = generate_file_name(url)
        file_path = plugin_cache_dir / file_name

        # 如果文件存在，则直接返回
        if file_path.exists():
            return file_path

        headers = {**COMMON_HEADER, **(ext_headers or {})}

        try:
            async with self.client.stream("GET", url, headers=headers, follow_redirects=True) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                content_length = int(content_length) if content_length else None

                if content_length and (file_size := content_length / 1024 / 1024) > MAX_SIZE:
                    logger.warning(f"预下载 {file_name} 大小 {file_size:.2f} MB 超过 {MAX_SIZE} MB 限制, 取消下载")
                    raise DownloadException("媒体大小超过配置限制，取消下载")

                with self.get_progress_bar(file_name, content_length) as bar:
                    async with aiofiles.open(file_path, "wb") as file:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            await file.write(chunk)
                            bar.update(len(chunk))

        except httpx.HTTPError:
            await safe_unlink(file_path)
            logger.exception(f"下载失败 | url: {url}, file_path: {file_path}")
            raise DownloadException("媒体下载失败")
        return file_path

    @staticmethod
    def get_progress_bar(desc: str, total: int | None = None) -> tqdm:
        """获取进度条 bar

        Args:
            desc (str): 描述
            total (int | None, optional): 总大小. Defaults to None.

        Returns:
            tqdm: 进度条
        """
        return tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            dynamic_ncols=True,
            colour="green",
            desc=desc,
        )

    async def download_video(
        self,
        url: str,
        *,
        video_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download video file by url with stream

        Args:
            url (str): url address
            video_name (str | None, optional): video name. Defaults to get name by parse url.
            ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

        Returns:
            Path: video file path

        Raises:
            httpx.HTTPError: When download fails
        """
        if video_name is None:
            video_name = generate_file_name(url, ".mp4")
        return await self.download_file_by_stream(url, file_name=video_name, ext_headers=ext_headers)

    async def download_audio(
        self,
        url: str,
        *,
        audio_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download audio file by url with stream

        Args:
            url (str): url address
            audio_name (str | None, optional): audio name. Defaults to get name by parse_url_resource_name.
            ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

        Returns:
            Path: audio file path

        Raises:
            httpx.HTTPError: When download fails
        """
        if audio_name is None:
            audio_name = generate_file_name(url, ".mp3")
        return await self.download_file_by_stream(url, file_name=audio_name, ext_headers=ext_headers)

    async def download_img(
        self,
        url: str,
        *,
        img_name: str | None = None,
        ext_headers: dict[str, str] | None = None,
    ) -> Path:
        """download image file by url with stream

        Args:
            url (str): url
            img_name (str, optional): image name. Defaults to None.
            ext_headers (dict[str, str], optional): ext headers. Defaults to None.

        Returns:
            Path: image file path

        Raises:
            httpx.HTTPError: When download fails
        """
        if img_name is None:
            img_name = generate_file_name(url, ".jpg")
        return await self.download_file_by_stream(url, file_name=img_name, ext_headers=ext_headers)

    async def download_imgs_without_raise(
        self,
        urls: list[str],
        *,
        ext_headers: dict[str, str] | None = None,
    ) -> list[Path]:
        """download images without raise

        Args:
            urls (list[str]): urls
            ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

        Returns:
            list[Path]: image file paths
        """
        paths_or_errs = await asyncio.gather(
            *[self.download_img(url, ext_headers=ext_headers) for url in urls], return_exceptions=True
        )
        return [p for p in paths_or_errs if isinstance(p, Path)]


DOWNLOADER: StreamDownloader = StreamDownloader()
