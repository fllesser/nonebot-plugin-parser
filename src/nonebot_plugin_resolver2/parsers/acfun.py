import json
from pathlib import Path
import re
from typing import ClassVar

import aiofiles
import httpx
from nonebot import logger

from ..config import MAX_SIZE, plugin_cache_dir
from ..constants import COMMON_TIMEOUT, DOWNLOAD_TIMEOUT
from ..download import DOWNLOADER
from ..exception import DownloadException, ParseException
from ..utils import safe_unlink
from .base import BaseParser
from .data import COMMON_HEADER, Author, ParseResult, Platform, VideoContent


class AcfunParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="acfun", display_name="猴山")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("acfun.cn", r"(?:ac=|/ac)(\d+)"),
    ]

    def __init__(self):
        self.headers = {"referer": "https://www.acfun.cn/", **COMMON_HEADER}

    async def parse_video_info(self, url: str) -> tuple[str, str, str, str, str]:
        """解析acfun链接获取详细信息

        Args:
            url (str): 链接

        Returns:
            tuple: (m3u8_url, title, description, author, upload_time)
        """
        # 拼接查询参数
        url = f"{url}?quickViewId=videoInfo_new&ajaxpipe=1"

        async with httpx.AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
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
        video_file = plugin_cache_dir / f"acfun_{acid}.mp4"
        if video_file.exists():
            return video_file

        try:
            max_size_in_bytes = MAX_SIZE * 1024 * 1024
            async with (
                aiofiles.open(video_file, "wb") as f,
                httpx.AsyncClient(headers=self.headers, timeout=DOWNLOAD_TIMEOUT) as client,
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
        except httpx.HTTPError:
            await safe_unlink(video_file)
            logger.exception("acfun 视频下载失败")
            raise DownloadException("acfun 视频下载失败")
        return video_file

    async def _parse_m3u8(self, m3u8_url: str):
        """解析m3u8链接

        Args:
            m3u8_url (str): m3u8链接

        Returns:
            list[str]: 视频链接
        """
        async with httpx.AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
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

    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配结果中提取 acid
        acid = int(matched.group(1))
        url = f"https://www.acfun.cn/v/ac{acid}"

        m3u8_url, title, description, author, upload_time = await self.parse_video_info(url)

        extra_info = f"简介: {description}\n上传于 {upload_time}" if description or upload_time else None

        # 下载视频
        video_path = await self.download_video(m3u8_url, acid)

        extra = {}
        if extra_info:
            extra["info"] = extra_info

        return ParseResult(
            title=title,
            platform=self.platform,
            content="",
            author=Author(name=author) if author else None,
            contents=[VideoContent(path=video_path)],
            extra=extra,
        )
