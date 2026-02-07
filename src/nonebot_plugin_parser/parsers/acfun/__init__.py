import re
import asyncio
from typing import ClassVar
from pathlib import Path
from urllib.parse import urljoin

import aiofiles
from httpx import HTTPError, AsyncClient
from nonebot import logger

from ..base import (
    DOWNLOADER,
    COMMON_TIMEOUT,
    DOWNLOAD_TIMEOUT,
    Platform,
    BaseParser,
    PlatformEnum,
    ParseException,
    DownloadException,
    DurationLimitException,
    handle,
    pconfig,
)


class AcfunParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.ACFUN, display_name="猴山")

    def __init__(self):
        super().__init__()
        self.headers["referer"] = "https://www.acfun.cn/"

    @handle("acfun.cn", r"(?:ac=|/ac)(?P<acid>\d+)")
    async def _parse(self, searched: re.Match[str]):
        acid = int(searched.group("acid"))
        url = f"https://www.acfun.cn/v/ac{acid}"

        video_info = await self.parse_video_info(url)
        author = self.create_author(video_info.name, video_info.avatar_url)

        video_task = asyncio.create_task(
            self.download_video(
                video_info.m3u8_url,
                f"acfun_{acid}.mp4",
                video_info.duration,
            )
        )

        video_content = self.create_video_content(video_task, cover_url=video_info.coverUrl)

        return self.result(
            title=video_info.title,
            text=video_info.text,
            author=author,
            timestamp=video_info.timestamp,
            contents=[video_content],
        )

    async def parse_video_info(self, url: str):
        """解析acfun链接获取详细信息

        Args:
            url (str): 链接

        Returns:
            video.VideoInfo
        """
        from . import video

        # 拼接查询参数
        url = f"{url}?quickViewId=videoInfo_new&ajaxpipe=1"

        async with AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw = response.text

        matched = re.search(r"window\.videoInfo =(.*?)</script>", raw)
        if not matched:
            raise ParseException("解析 acfun 视频信息失败")

        raw = str(matched.group(1))
        raw = re.sub(r'\\{1,4}"', '"', raw)
        raw = raw.replace('"{', "{").replace('}"', "}")
        return video.decoder.decode(raw)

    async def download_video(self, m3u8_url: str, file_name: str, duration: int) -> Path:
        """下载acfun视频

        Args:
            m3u8_url (str): m3u8链接
            file_name (str): 文件名
            duration (int): 视频时长(秒)

        Returns:
            Path: 下载的mp4文件
        """

        if duration >= pconfig.duration_maximum:
            raise DurationLimitException

        video_file = pconfig.cache_dir / file_name
        if video_file.exists():
            return video_file

        m3u8_slices = await self._get_m3u8_slices(m3u8_url)

        try:
            async with (
                aiofiles.open(video_file, "wb") as f,
                AsyncClient(headers=self.headers, timeout=DOWNLOAD_TIMEOUT) as client,
            ):
                total_size = 0
                async with DOWNLOADER.manual_progress(desc=file_name) as update:
                    for url in m3u8_slices:
                        async with client.stream("GET", url) as response:
                            async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                                await f.write(chunk)
                                total_size += len(chunk)
                                update(advance=len(chunk))
        except HTTPError:
            video_file.unlink(missing_ok=True)
            logger.exception("视频下载失败")
            raise DownloadException("视频下载失败")
        return video_file

    async def _get_m3u8_slices(self, m3u8_url: str):
        """拼接m3u8链接

        Args:
            m3u8_url (str): m3u8链接
            m3u8_slice (str): m3u8切片

        Returns:
            list[str]: 视频链接
        """
        async with AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(m3u8_url)
            response.raise_for_status()

        slices: list[str] = []
        for line in response.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            slices.append(urljoin(m3u8_url, line))

        return slices
