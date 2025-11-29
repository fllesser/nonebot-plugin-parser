import re
import json
import time
import asyncio
from typing import ClassVar
from pathlib import Path

import aiofiles
from httpx import HTTPError, AsyncClient
from nonebot import logger

from .base import DOWNLOADER, Platform, BaseParser, PlatformEnum, handle, pconfig
from ..utils import safe_unlink
from ..constants import COMMON_TIMEOUT, DOWNLOAD_TIMEOUT
from ..exception import ParseException, DownloadException


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

        m3u8_url, title, description, author, upload_time = await self.parse_video_info(url)
        author = self.create_author(author) if author else None

        # 2024-12-1 -> timestamp
        timestamp = int(time.mktime(time.strptime(upload_time, "%Y-%m-%d")))
        text = f"简介: {description}"

        # 下载视频
        video_task = asyncio.create_task(self.download_video(m3u8_url, acid))

        return self.result(
            title=title,
            text=text,
            author=author,
            timestamp=timestamp,
            contents=[self.create_video_content(video_task)],
        )

    async def parse_video_info(self, url: str) -> tuple[str, str, str, str, str]:
        """解析acfun链接获取详细信息

        Args:
            url (str): 链接

        Returns:
            tuple: (m3u8_url, title, description, author, upload_time)
        """

        # 拼接查询参数
        url = f"{url}?quickViewId=videoInfo_new&ajaxpipe=1"

        async with AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw = response.text

        matched = re.search(r"window\.videoInfo =(.*?)</script>", raw)
        if not matched:
            raise ParseException("解析 acfun 视频信息失败")
        json_str = str(matched.group(1))
        json_str = json_str.replace('\\\\"', '\\"').replace('\\"', '"')
        video_info = json.loads(json_str)

        title = video_info.get("title", "")
        description = video_info.get("description", "")
        author = video_info.get("user", {}).get("name", "")
        upload_time = video_info.get("createTime", "")

        ks_play_json = video_info["currentVideoInfo"]["ksPlayJson"]
        ks_play = json.loads(ks_play_json)
        representations = ks_play["adaptationSet"][0]["representation"]
        # 这里[d['url'] for d in representations]，从 4k ~ 360，此处默认720p
        m3u8_url = [d["url"] for d in representations][3]

        return m3u8_url, title, description, author, upload_time

    async def download_video(self, m3u8s_url: str, acid: int) -> Path:
        """下载acfun视频

        Args:
            m3u8s_url (str): m3u8链接
            acid (int): acid

        Returns:
            Path: 下载的mp4文件
        """

        m3u8_full_urls = await self._parse_m3u8(m3u8s_url)
        video_file = pconfig.cache_dir / f"acfun_{acid}.mp4"
        if video_file.exists():
            return video_file

        try:
            max_size_in_bytes = pconfig.max_size * 1024 * 1024
            async with (
                aiofiles.open(video_file, "wb") as f,
                AsyncClient(headers=self.headers, timeout=DOWNLOAD_TIMEOUT) as client,
            ):
                total_size = 0
                with DOWNLOADER.get_progress_bar(video_file.name) as bar:
                    for url in m3u8_full_urls:
                        async with client.stream("GET", url) as response:
                            async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                                await f.write(chunk)
                                total_size += len(chunk)
                                bar.update(len(chunk))
                        if total_size > max_size_in_bytes:
                            # 直接截断
                            break
        except HTTPError:
            await safe_unlink(video_file)
            logger.exception("视频下载失败")
            raise DownloadException("视频下载失败")
        return video_file

    async def _parse_m3u8(self, m3u8_url: str):
        """解析m3u8链接

        Args:
            m3u8_url (str): m3u8链接

        Returns:
            list[str]: 视频链接
        """
        async with AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(m3u8_url)
            m3u8_file = response.text
        # 分离ts文件链接
        raw_pieces = re.split(r"\n#EXTINF:.{8},\n", m3u8_file)
        # 过滤头部\
        m3u8_relative_links = raw_pieces[1:]

        # 修改尾部 去掉尾部多余的结束符
        patched_tail = m3u8_relative_links[-1].split("\n")[0]
        m3u8_relative_links[-1] = patched_tail

        # 完整链接，直接加 m3u8Url 的通用前缀
        m3u8_prefix = "/".join(m3u8_url.split("/")[0:-1])
        m3u8_full_urls = [f"{m3u8_prefix}/{d}" for d in m3u8_relative_links]

        return m3u8_full_urls
