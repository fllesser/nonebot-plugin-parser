import re
from typing import Any, ClassVar

import httpx

from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..download import DOWNLOADER
from ..exception import ParseException
from .base import BaseParser
from .data import Content, DynamicContent, ImageContent, ParseResult, Platform, VideoContent


class TwitterParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="twitter", display_name="小蓝鸟")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("x.com", r"https?://x.com/[0-9-a-zA-Z_]{1,20}/status/([0-9]+)"),
    ]

    @staticmethod
    async def _req_xdown_api(url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://xdown.app",
            "Referer": "https://xdown.app/",
            **COMMON_HEADER,
        }
        data = {"q": url, "lang": "zh-cn"}
        async with httpx.AsyncClient(headers=headers, timeout=COMMON_TIMEOUT) as client:
            url = "https://xdown.app/api/ajaxSearch"
            response = await client.post(url, data=data)
            return response.json()

    @classmethod
    async def parse_x_url(cls, x_url: str) -> list[Content]:
        resp = await cls._req_xdown_api(x_url)
        if resp.get("status") != "ok":
            raise ParseException("解析失败")

        html_content = resp.get("data")

        if html_content is None:
            raise ParseException("解析失败, 数据为空")

        first_video_url = await cls._get_first_video_url(html_content)
        if first_video_url is not None:
            video_path = await DOWNLOADER.download_video(first_video_url)
            return [VideoContent(video_path)]

        contents: list[Content] = []
        pic_urls = await cls._get_all_pic_urls(html_content)
        dynamic_urls = await cls._get_all_gif_urls(html_content)
        if len(pic_urls) != 0:
            # 下载图片和动态图
            pic_paths = await DOWNLOADER.download_imgs_without_raise(pic_urls)
            dynamic_paths = []
            if dynamic_urls:
                from asyncio import gather
                from pathlib import Path

                results = await gather(
                    *[DOWNLOADER.download_video(url) for url in dynamic_urls], return_exceptions=True
                )
                dynamic_paths = [p for p in results if isinstance(p, Path)]

            contents.extend(ImageContent(path) for path in pic_paths)
            contents.extend(DynamicContent(path) for path in dynamic_paths)

        return contents

    @classmethod
    def _snapcdn_url_pattern(cls, flag: str) -> re.Pattern[str]:
        """
        根据标志生成正则表达式模板
        """
        # 非贪婪匹配 href 中的 URL，确保匹配到正确的下载链接
        pattern = rf'href="(https?://dl\.snapcdn\.app/get\?token=.*?)".*?下载{flag}'
        return re.compile(pattern, re.DOTALL)  # 允许.匹配换行符

    @classmethod
    async def _get_first_video_url(cls, html_content: str) -> str | None:
        """
        使用正则表达式简单提取第一个视频下载链接
        """
        # 匹配第一个视频下载链接
        matched = re.search(cls._snapcdn_url_pattern(" MP4"), html_content)
        return matched.group(1) if matched else None

    @classmethod
    async def _get_all_pic_urls(cls, html_content: str) -> list[str]:
        """
        提取所有图片链接
        """
        return re.findall(cls._snapcdn_url_pattern("图片"), html_content)

    @classmethod
    async def _get_all_gif_urls(cls, html_content: str) -> list[str]:
        """
        提取所有 GIF 链接
        """
        return re.findall(cls._snapcdn_url_pattern(" gif"), html_content)

    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        url = matched.group(0)
        contents = await self.parse_x_url(url)

        if contents is None:
            raise ParseException("解析失败，未找到内容")

        return ParseResult(
            title="",  # 推特解析不包含标题
            platform=self.platform,
            contents=contents,
        )
