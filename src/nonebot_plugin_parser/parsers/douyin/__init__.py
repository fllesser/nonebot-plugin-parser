import re
from typing import ClassVar
from typing_extensions import override

import httpx
import msgspec
from nonebot import logger

from ...constants import COMMON_TIMEOUT
from ...download import DOWNLOADER
from ...exception import ParseException
from ..base import BaseParser
from ..data import (
    ANDROID_HEADER,
    IOS_HEADER,
    Author,
    DynamicContent,
    ImageContent,
    MediaContent,
    ParseResult,
    Platform,
    VideoContent,
)


class DouyinParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="douyin", display_name="抖音")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("v.douyin", r"https://v\.douyin\.com/[a-zA-Z0-9_\-]+"),
        (
            "douyin",
            r"https://www\.(?:douyin|iesdouyin)\.com/(?:video|note|share/(?:video|note|slides))/[0-9]+",
        ),
    ]

    def __init__(self):
        self.ios_headers = IOS_HEADER.copy()
        self.android_headers = {"Accept": "application/json, text/plain, */*", **ANDROID_HEADER}

    def _build_iesdouyin_url(self, _type: str, video_id: str) -> str:
        return f"https://www.iesdouyin.com/share/{_type}/{video_id}"

    def _build_m_douyin_url(self, _type: str, video_id: str) -> str:
        return f"https://m.douyin.com/share/{_type}/{video_id}"

    async def parse_share_url(self, share_url: str) -> ParseResult:
        if matched := re.match(r"(video|note)/([0-9]+)", share_url):
            # https://www.douyin.com/video/xxxxxx
            _type, video_id = matched.group(1), matched.group(2)
            iesdouyin_url = self._build_iesdouyin_url(_type, video_id)
        else:
            # https://v.douyin.com/xxxxxx
            iesdouyin_url = await self.get_redirect_url(share_url)
            # https://www.iesdouyin.com/share/video/7468908569061100857/?region=CN&mid=0&u_
            matched = re.search(r"(slides|video|note)/(\d+)", iesdouyin_url)
            if not matched:
                raise ParseException(f"无法从 {share_url} 中解析出 ID")
            _type, video_id = matched.group(1), matched.group(2)
            if _type == "slides":
                return await self.parse_slides(video_id)
        for url in [
            self._build_m_douyin_url(_type, video_id),
            share_url,
            iesdouyin_url,
        ]:
            try:
                return await self.parse_video(url)
            except ParseException as e:
                logger.warning(f"failed to parse {url[:60]}, error: {e}")
                continue
        raise ParseException("分享已删除或资源直链获取失败, 请稍后再试")

    async def parse_video(self, url: str) -> ParseResult:
        async with httpx.AsyncClient(
            headers=self.ios_headers,
            timeout=COMMON_TIMEOUT,
            follow_redirects=False,
            verify=False,
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise ParseException(f"status: {response.status_code}")
            text = response.text

        video_data = self._extract_data(text)

        # 下载封面
        cover_path = None
        if video_data.cover_url:
            cover_path = DOWNLOADER.download_img(video_data.cover_url)

        # 下载内容
        contents: list[MediaContent] = []
        if image_urls := video_data.images_urls:
            contents.extend(ImageContent(DOWNLOADER.download_img(url)) for url in image_urls)
        elif video_url := video_data.video_url:
            video_url = await self.get_redirect_url(video_url)
            contents.append(VideoContent(DOWNLOADER.download_video(video_url), cover_path))

        return self.result(
            text=video_data.desc,
            author=Author(name=video_data.author.nickname) if video_data.author.nickname else None,
            contents=contents,
        )

    def _extract_data(self, text: str):
        """从html中提取视频数据

        Args:
            text (str): 网页源码

        Raises:
            ParseException: 解析失败

        Returns:
            VideoData: 数据
        """
        pattern = re.compile(
            pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        matched = pattern.search(text)

        if not matched or not matched.group(1):
            raise ParseException("can't find _ROUTER_DATA in html")

        from .video import RouterData

        return msgspec.json.decode(matched.group(1).strip(), type=RouterData).video_data

    async def parse_slides(self, video_id: str) -> ParseResult:
        url = "https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/"
        params = {
            "aweme_ids": f"[{video_id}]",
            "request_source": "200",
        }
        async with httpx.AsyncClient(headers=self.android_headers, verify=False) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        from .slides import SlidesInfo

        slides_data = msgspec.json.decode(response.content, type=SlidesInfo).aweme_details[0]
        # 下载图片
        contents: list[MediaContent] = []
        contents.extend(ImageContent(DOWNLOADER.download_img(url)) for url in slides_data.images_urls)

        if slides_data.dynamic_urls:
            contents.extend(DynamicContent(DOWNLOADER.download_video(url)) for url in slides_data.dynamic_urls)

        author = Author(name=slides_data.name, avatar=DOWNLOADER.download_img(slides_data.avatar_url))

        return self.result(
            title=slides_data.desc,
            timestamp=slides_data.create_time,
            author=author,
            contents=contents,
        )

    @override
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
        return await self.parse_share_url(url)
