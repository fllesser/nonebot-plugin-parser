import random
import re
from typing import ClassVar

import httpx
import msgspec

from ..constants import COMMON_HEADER, COMMON_TIMEOUT, IOS_HEADER
from ..exception import ParseException
from .base import BaseParser
from .data import ImageContent, ParseResult, VideoContent
from .utils import get_redirect_url


class KuaishouParser(BaseParser):
    """快手解析器"""

    # 平台名称（用于配置禁用和内部标识）
    platform_name: ClassVar[str] = "kuaishou"

    # 平台显示名称
    platform_display_name: ClassVar[str] = "快手"

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

    async def parse_url(self, url: str) -> ParseResult:
        """解析快手链接获取视频信息

        Args:
            url: 快手视频链接

        Returns:
            ParseResult: 快手视频信息
        """
        location_url = await get_redirect_url(url, headers=self.v_headers)

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

        return await photo.convert_parse_result(self.platform_display_name, self.v_headers)


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

    async def convert_parse_result(
        self, platform: str = "快手", ext_headers: dict[str, str] | None = None
    ) -> ParseResult:
        from ..download import DOWNLOADER

        # 下载封面
        cover_path = None
        if self.cover_url:
            cover_path = await DOWNLOADER.download_img(self.cover_url, ext_headers=ext_headers)

        # 下载内容
        content = None
        if video_url := self.video_url:
            video_path = await DOWNLOADER.download_video(video_url, ext_headers=ext_headers)
            content = VideoContent(video_path=video_path)
        elif img_urls := self.img_urls:
            pic_paths = await DOWNLOADER.download_imgs_without_raise(img_urls, ext_headers=ext_headers)
            content = ImageContent(pic_paths=pic_paths)

        return ParseResult(title=self.caption, platform=platform, cover_path=cover_path, content=content)


class TusjohData(Struct):
    result: int
    photo: Photo | None = None


KuaishouInitState: TypeAlias = dict[str, TusjohData]
