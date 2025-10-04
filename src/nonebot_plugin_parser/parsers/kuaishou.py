import asyncio
import random
import re
from typing import ClassVar

import httpx
import msgspec

from ..constants import COMMON_HEADER, COMMON_TIMEOUT, IOS_HEADER
from ..download import DOWNLOADER
from ..exception import ParseException
from .base import BaseParser
from .data import Content, ImageContent, ParseResult, Platform, VideoContent


class KuaiShouParser(BaseParser):
    """快手解析器"""

    # 平台信息
    platform: ClassVar[Platform] = Platform(name="kuaishou", display_name="快手")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("v.kuaishou.com", r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
        ("kuaishou", r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
        ("chenzhongtech", r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
    ]

    def __init__(self):
        self.headers = COMMON_HEADER
        self.v_headers = {
            **IOS_HEADER,
            "Referer": "https://v.kuaishou.com/",
        }

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
        location_url = await self.get_redirect_url(url, headers=self.v_headers)

        if len(location_url) <= 0:
            raise ParseException("failed to get location url from url")

        # /fw/long-video/ 返回结果不一样, 统一替换为 /fw/photo/ 请求
        location_url = location_url.replace("/fw/long-video/", "/fw/photo/")

        async with httpx.AsyncClient(headers=self.v_headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(location_url)
            response.raise_for_status()
            response_text = response.text

        pattern = r"window\.INIT_STATE\s*=\s*(.*?)</script>"
        searched = re.search(pattern, response_text)

        if not searched:
            raise ParseException("failed to parse video JSON info from HTML")

        json_str = searched.group(1).strip()
        init_state = msgspec.json.decode(json_str, type=KuaishouInitState)
        photo = next((d.photo for d in init_state.values() if d.photo is not None), None)
        if photo is None:
            raise ParseException("window.init_state don't contains videos or pics")

        return await self._photo2result(photo)

    async def _photo2result(self, photo: "Photo"):
        # 下载封面
        cover_path = None
        if photo.cover_url:
            cover_path = await DOWNLOADER.download_img(photo.cover_url, ext_headers=self.headers)

        # 下载内容
        contents: list[Content] = []
        if video_url := photo.video_url:
            video_task = asyncio.create_task(DOWNLOADER.download_video(video_url, ext_headers=self.headers))
            contents.append(VideoContent(video_task))
        elif img_urls := photo.img_urls:
            pic_paths = await DOWNLOADER.download_imgs_without_raise(img_urls, ext_headers=self.headers)
            contents.extend(ImageContent(path) for path in pic_paths)

        return self.result(title=photo.caption, cover_path=cover_path, contents=contents)


from typing import TypeAlias

from msgspec import Struct, field


class CdnUrl(Struct):
    cdn: str
    url: str | None = None


class Atlas(Struct):
    music_cdn_list: list[CdnUrl] = field(name="musicCdnList", default_factory=list)
    cdn_list: list[CdnUrl] = field(name="cdnList", default_factory=list)
    size: list[dict] = field(name="size", default_factory=list)
    img_route_list: list[str] = field(name="list", default_factory=list)

    @property
    def img_urls(self):
        if len(self.cdn_list) == 0 or len(self.img_route_list) == 0:
            return None
        cdn = random.choice(self.cdn_list).cdn
        return [f"https://{cdn}/{url}" for url in self.img_route_list]


class ExtParams(Struct):
    atlas: Atlas = field(default_factory=Atlas)


class Photo(Struct):
    # 标题
    caption: str
    cover_urls: list[CdnUrl] = field(name="coverUrls", default_factory=list)
    main_mv_urls: list[CdnUrl] = field(name="mainMvUrls", default_factory=list)
    ext_params: ExtParams = field(name="ext_params", default_factory=ExtParams)

    @property
    def cover_url(self):
        return random.choice(self.cover_urls).url if len(self.cover_urls) != 0 else None

    @property
    def video_url(self):
        return random.choice(self.main_mv_urls).url if len(self.main_mv_urls) != 0 else None

    @property
    def img_urls(self):
        return self.ext_params.atlas.img_urls


class TusjohData(Struct):
    result: int
    photo: Photo | None = None


KuaishouInitState: TypeAlias = dict[str, TusjohData]
