import re
from typing import Any, ClassVar

import httpx
from nonebot import logger

from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..exception import ParseException
from .base import BaseParser
from .data import ImageContent, ParseResult, VideoContent


class TwitterParser(BaseParser):
    # 平台名称（用于配置禁用和内部标识）
    platform_name: ClassVar[str] = "twitter"

    # 平台显示名称
    platform_display_name: ClassVar[str] = "小蓝鸟"

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("x.com", r"https?://x.com/[0-9-a-zA-Z_]{1,20}/status/([0-9]+)"),
    ]

    @staticmethod
    async def req_xdown_api(url: str) -> dict[str, Any]:
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
    async def parse_x_url(cls, x_url: str):
        resp = await cls.req_xdown_api(x_url)
        if resp.get("status") != "ok":
            raise ParseException("解析失败")

        html_content = resp.get("data")

        if html_content is None:
            raise ParseException("解析失败, 数据为空")

        logger.debug(f"html_content: {html_content}")

        # 导入下载器
        from ..download import DOWNLOADER

        first_video_url = await cls.get_first_video_url(html_content)
        if first_video_url is not None:
            video_path = await DOWNLOADER.download_video(first_video_url)
            return VideoContent(video_path=video_path)

        pic_urls = await cls.get_all_pic_urls(html_content)
        dynamic_urls = await cls.get_all_gif_urls(html_content)
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
            return ImageContent(pic_paths=pic_paths, dynamic_paths=dynamic_paths)

    @classmethod
    def snapcdn_url_pattern(cls, flag: str) -> re.Pattern[str]:
        """
        根据标志生成正则表达式模板
        """
        # 非贪婪匹配 href 中的 URL，确保匹配到正确的下载链接
        pattern = rf'href="(https?://dl\.snapcdn\.app/get\?token=.*?)".*?下载{flag}'
        return re.compile(pattern, re.DOTALL)  # 允许.匹配换行符

    @classmethod
    async def get_first_video_url(cls, html_content: str) -> str | None:
        """
        使用正则表达式简单提取第一个视频下载链接
        """
        # 匹配第一个视频下载链接
        matched = re.search(cls.snapcdn_url_pattern(" MP4"), html_content)
        return matched.group(1) if matched else None

    @classmethod
    async def get_all_pic_urls(cls, html_content: str) -> list[str]:
        """
        提取所有图片链接
        """
        return re.findall(cls.snapcdn_url_pattern("图片"), html_content)

    @classmethod
    async def get_all_gif_urls(cls, html_content: str) -> list[str]:
        """
        提取所有 GIF 链接
        """
        return re.findall(cls.snapcdn_url_pattern(" gif"), html_content)

    async def parse_url(self, url: str) -> ParseResult:
        """解析推特/X URL（标准接口）

        Args:
            url: 推特链接

        Returns:
            ParseResult: 解析结果（仅包含 URL，不下载）

        Raises:
            ParseException: 解析失败
        """
        content = await self.parse_x_url(url)

        if content is None:
            raise ParseException("解析失败，未找到内容")

        return ParseResult(
            title="",  # 推特解析不包含标题
            platform=self.platform_display_name,
            content=content,
        )
