import random
import re

import httpx
import msgspec

from ..constants import COMMON_HEADER, COMMON_TIMEOUT, IOS_HEADER
from ..exception import ParseException
from .data import ImageContent, ParseResult, VideoContent
from .utils import get_redirect_url


class KuaishouParser:
    """快手解析器"""

    def __init__(self):
        self.headers = COMMON_HEADER
        self.v_headers = {
            **IOS_HEADER,
            "Referer": "https://v.kuaishou.com/",
        }
        self.platform = "快手"

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

        return photo.convert_parse_result(self.platform)


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

    def convert_parse_result(self, platform: str = "快手") -> ParseResult:
        if video_url := self.video_url:
            content = VideoContent(video_url=video_url)
        elif img_urls := self.img_urls:
            content = ImageContent(pic_urls=img_urls)
        else:
            content = None
        return ParseResult(title=self.caption, platform=platform, cover_url=self.cover_url, content=content)


class TusjohData(Struct):
    result: int
    photo: Photo | None = None


KuaishouInitState: TypeAlias = dict[str, TusjohData]
