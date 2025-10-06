from itertools import chain
import re
from typing import Any, ClassVar

import httpx

from ..exception import ParseException
from .base import BaseParser
from .data import ParseResult, Platform


class TwitterParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="twitter", display_name="小蓝鸟")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("x.com", r"https?://x.com/[0-9-a-zA-Z_]{1,20}/status/([0-9]+)"),
    ]

    async def _req_xdown_api(self, url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://xdown.app",
            "Referer": "https://xdown.app/",
            **self.headers,
        }
        data = {"q": url, "lang": "zh-cn"}
        async with httpx.AsyncClient(headers=headers, timeout=self.timeout) as client:
            url = "https://xdown.app/api/ajaxSearch"
            response = await client.post(url, data=data)
            return response.json()

    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path)

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        url = matched.group(0)
        resp = await self._req_xdown_api(url)
        if resp.get("status") != "ok":
            raise ParseException("解析失败")

        html_content = resp.get("data")

        if html_content is None:
            raise ParseException("解析失败, 数据为空")

        data = self.parse_twitter_html(html_content)

        return self.build_result(data)

    @classmethod
    def parse_twitter_html(cls, html_content: str):
        """解析 Twitter HTML 内容

        Args:
            html_content (str): Twitter HTML 内容

        Returns:
            ParseData: 解析数据
        """
        from bs4 import BeautifulSoup, Tag

        from .data import ParseData

        soup = BeautifulSoup(html_content, "html.parser")
        data = ParseData(name="无用户名")

        # 1. 提取缩略图链接
        thumb_tag = soup.find("img")
        if isinstance(thumb_tag, Tag):
            if cover := thumb_tag.get("src"):
                data.cover_url = str(cover)

        # 2. 提取下载链接
        tw_button_tags = soup.find_all("a", class_="tw-button-dl")
        abutton_tags = soup.find_all("a", class_="abutton")
        for tag in chain(tw_button_tags, abutton_tags):
            if not isinstance(tag, Tag):
                continue
            href = tag.get("href")
            if href is None:
                continue

            href = str(href)
            text = tag.get_text(strip=True)
            if "下载 MP4" in text:
                data.video_url = href
                break
            elif "下载图片" in text:
                data.images_urls.append(href)
            elif "下载 gif" in text:
                data.dynamic_urls.append(href)

        # 3. 提取标题
        title_tag = soup.find("h3")
        if title_tag:
            data.title = title_tag.get_text(strip=True)

        return data
        # # 4. 提取Twitter ID
        # twitter_id_input = soup.find("input", {"id": "TwitterId"})
        # if (
        #     twitter_id_input
        #     and isinstance(twitter_id_input, Tag)
        #     and (value := twitter_id_input.get("value"))
        #     and isinstance(value, str)
        # ):
