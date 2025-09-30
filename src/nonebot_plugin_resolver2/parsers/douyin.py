import asyncio
from pathlib import Path
import re
from typing import Any, ClassVar

import httpx
import msgspec
from nonebot import logger

from ..constants import COMMON_TIMEOUT
from ..download import DOWNLOADER
from ..exception import ParseException
from .base import BaseParser
from .data import ANDROID_HEADER, IOS_HEADER, ImageContent, ParseResult, VideoContent
from .utils import get_redirect_url


class DouyinParser(BaseParser):
    # 平台名称（用于配置禁用和内部标识）
    platform_name: ClassVar[str] = "douyin"

    # 平台显示名称
    platform_display_name: ClassVar[str] = "抖音"

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
            iesdouyin_url = await get_redirect_url(share_url)
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
        content = None
        if image_urls := video_data.images_urls:
            content = ImageContent(pic_urls=image_urls)
        elif video_url := video_data.video_url:
            content = VideoContent(video_url=await get_redirect_url(video_url))

        return ParseResult(
            title=video_data.desc,
            platform=self.platform_display_name,
            cover_url=video_data.cover_url,
            author=video_data.author.nickname,
            content=content,
        )

    def _extract_data(self, text: str) -> "VideoData":
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

        slides_data = msgspec.json.decode(response.content, type=SlidesInfo).aweme_details[0]

        return ParseResult(
            title=slides_data.share_info.share_desc_info,
            platform=self.platform_display_name,
            cover_url="",
            author=slides_data.author.nickname,
            content=ImageContent(pic_urls=slides_data.images_urls, dynamic_urls=slides_data.dynamic_urls),
        )

    async def parse_url(self, url: str) -> ParseResult:
        """解析抖音分享链接（标准接口）

        Args:
            url: 分享链接

        Returns:
            ParseResult: 解析结果（仅包含 URL，不下载）
        """
        return await self.parse_share_url(url)

    async def parse_and_download(self, share_url: str) -> ParseResult:
        """解析并下载抖音视频/图片（向后兼容的方法）

        Args:
            share_url (str): 分享链接

        Returns:
            ParseResult: 包含下载后文件路径的解析结果
        """
        # 先解析获取 URL
        result = await self.parse_url(share_url)

        # 下载封面
        if result.cover_url:
            result.cover_path = await DOWNLOADER.download_img(result.cover_url)

        # 下载内容
        if result.content:
            if isinstance(result.content, VideoContent) and result.content.video_url:
                result.content.video_path = await DOWNLOADER.download_video(result.content.video_url)
            elif isinstance(result.content, ImageContent):
                # 下载普通图片
                if result.content.pic_urls:
                    result.content.pic_paths = await DOWNLOADER.download_imgs_without_raise(result.content.pic_urls)
                # 下载动态图片
                if result.content.dynamic_urls:
                    video_paths = await asyncio.gather(
                        *[DOWNLOADER.download_video(url) for url in result.content.dynamic_urls],
                        return_exceptions=True,
                    )
                    result.content.dynamic_paths = [p for p in video_paths if isinstance(p, Path)]

        return result


from msgspec import Struct, field


class PlayAddr(Struct):
    url_list: list[str]


class Cover(Struct):
    url_list: list[str]


class Video(Struct):
    play_addr: PlayAddr
    cover: Cover


class Image(Struct):
    video: Video | None = None
    url_list: list[str] = field(default_factory=list)


class ShareInfo(Struct):
    share_desc_info: str


class Author(Struct):
    nickname: str


class SlidesData(Struct):
    author: Author
    share_info: ShareInfo
    images: list[Image]

    @property
    def images_urls(self) -> list[str]:
        return [image.url_list[0] for image in self.images]

    @property
    def dynamic_urls(self) -> list[str]:
        return [image.video.play_addr.url_list[0] for image in self.images if image.video]


class SlidesInfo(Struct):
    aweme_details: list[SlidesData] = field(default_factory=list)


class VideoData(Struct):
    author: Author
    desc: str
    images: list[Image] | None = None
    video: Video | None = None

    @property
    def images_urls(self) -> list[str] | None:
        return [image.url_list[0] for image in self.images] if self.images else None

    @property
    def video_url(self) -> str | None:
        return self.video.play_addr.url_list[0].replace("playwm", "play") if self.video else None

    @property
    def cover_url(self) -> str | None:
        return self.video.cover.url_list[0] if self.video else None


class VideoInfoRes(Struct):
    item_list: list[VideoData] = field(default_factory=list)

    @property
    def video_data(self) -> VideoData:
        if len(self.item_list) == 0:
            raise ParseException("can't find data in videoInfoRes")
        return self.item_list[0]


class VideoOrNotePage(Struct):
    videoInfoRes: VideoInfoRes


class LoaderData(Struct):
    video_page: VideoOrNotePage | None = field(name="video_(id)/page", default=None)
    note_page: VideoOrNotePage | None = field(name="note_(id)/page", default=None)


class RouterData(Struct):
    loaderData: LoaderData
    errors: dict[str, Any] | None = None

    @property
    def video_data(self) -> VideoData:
        if page := self.loaderData.video_page:
            return page.videoInfoRes.video_data
        elif page := self.loaderData.note_page:
            return page.videoInfoRes.video_data
        raise ParseException("can't find video_(id)/page or note_(id)/page in router data")
