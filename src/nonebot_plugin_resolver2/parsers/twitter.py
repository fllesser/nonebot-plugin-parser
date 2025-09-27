import re
from typing import Any

import httpx
from nonebot import logger

from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..exception import ParseException
from .data import ImageContent, VideoContent


class TwitterParser:
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

        first_video_url = await cls.get_first_video_url(html_content)
        if first_video_url is not None:
            return VideoContent(video_url=first_video_url)

        pic_urls = await cls.get_all_pic_urls(html_content)
        dynamic_urls = await cls.get_all_gif_urls(html_content)
        if len(pic_urls) != 0:
            return ImageContent(pic_urls=pic_urls, dynamic_urls=dynamic_urls)

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
