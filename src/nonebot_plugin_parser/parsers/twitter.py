import re
from typing import Any, Literal, ClassVar
from itertools import chain

from httpx import AsyncClient
from msgspec import Struct, field
from msgspec.json import Decoder

from .base import BaseParser, PlatformEnum, handle
from .data import Platform, ParseResult
from ..exception import ParseException


class MediaElement(Struct):
    type: Literal["video", "image", "gif"]
    url: str
    altText: str | None = None
    thumbnail_url: str | None = None
    duration_millis: int | None = None

    @property
    def duration(self) -> float | None:
        return self.duration_millis / 1000 if self.duration_millis else None


class Article(Struct):
    image: str | None = None
    preview_text: str | None = None
    title: str | None = None


class VxTwitterResponse(Struct):
    article: str | Article | None
    date_epoch: int
    fetched_on: int
    likes: int
    text: str
    user_name: str
    user_screen_name: str
    user_profile_image_url: str
    qrt: "VxTwitterResponse | None" = None
    qrtURL: str | None = None
    media_extended: list[MediaElement] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"{self.user_name} @{self.user_screen_name}"


decoder = Decoder(VxTwitterResponse)


class TwitterParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.TWITTER, display_name="小蓝鸟")

    @handle("x.com", r"x.com/[0-9-a-zA-Z_]{1,20}/status/([0-9]+)")
    async def _parse(self, searched: re.Match[str]) -> ParseResult:
        url = f"https://{searched.group(0)}"
        return await self.parse_by_vxapi(url)

    async def parse_by_vxapi(self, url: str):
        """使用 vxtwitter API 解析 Twitter 链接"""

        api_url = url.replace("x.com", "api.vxtwitter.com")
        async with AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.get(api_url)
            response.raise_for_status()

        data = decoder.decode(response.content)
        return self._collect_result(data)

    def _collect_result(self, data: VxTwitterResponse) -> ParseResult:
        author = self.create_author(data.user_name, data.user_profile_image_url)
        title = data.article.title if isinstance(data.article, Article) else data.article

        result = self.result(
            author=author,
            title=title,
            text=data.text,
            timestamp=data.date_epoch,
        )

        for media in data.media_extended:
            if media.type == "video":
                result.video = self.create_video_content(
                    media.url,
                    media.thumbnail_url,
                    duration=media.duration,
                )
                break
            elif media.type == "image":
                result.contents.append(self.create_image_content(media.url))
            elif media.type == "gif":
                result.contents.append(self.create_dynamic_content(media.url))

        result.repost = self._collect_result(data.qrt) if data.qrt else None

        return result

    async def _parse_old(self, searched: re.Match[str]) -> ParseResult:
        # 从匹配对象中获取原始URL
        url = f"https://{searched.group(0)}"

        resp = await self._req_xdown_api(url)
        if resp.get("status") != "ok":
            raise ParseException("解析失败")

        html_content = resp.get("data")

        if html_content is None:
            raise ParseException("解析失败, 数据为空")

        return self._parse_twitter_html(html_content)

    async def _req_xdown_api(self, url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://xdown.app",
            "Referer": "https://xdown.app/",
            **self.headers,
        }
        data = {"q": url, "lang": "zh-cn"}
        async with AsyncClient(headers=headers, timeout=self.timeout) as client:
            url = "https://xdown.app/api/ajaxSearch"
            response = await client.post(url, data=data)
            return response.json()

    def _parse_twitter_html(self, html_content: str) -> ParseResult:
        """解析 Twitter HTML 内容"""
        from bs4 import Tag, BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # 初始化数据
        cover_url = None
        result = self.result()

        # 1. 提取缩略图链接
        thumb_tag = soup.find("img")
        if isinstance(thumb_tag, Tag):
            if cover := thumb_tag.get("src"):
                cover_url = str(cover)

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
                result.video = self.create_video_content(href, cover_url)
                break
            elif "下载图片" in text:
                result.contents.append(self.create_image_content(href))
            elif "下载 gif" in text:
                result.contents.append(self.create_dynamic_content(href))

        # 3. 提取标题
        title_tag = soup.find("h3")
        if title_tag:
            result.title = title_tag.get_text(strip=True)

        return result
