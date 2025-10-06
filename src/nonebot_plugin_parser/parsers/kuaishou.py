import random
import re
from typing import ClassVar

import httpx
import msgspec

from ..exception import ParseException
from .base import BaseParser
from .data import ParseData, ParseResult, Platform


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
        super().__init__()
        self.ios_headers["Referer"] = "https://v.kuaishou.com/"

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
        location_url = await self.get_redirect_url(url, headers=self.ios_headers)

        if len(location_url) <= 0:
            raise ParseException("failed to get location url from url")

        # /fw/long-video/ 返回结果不一样, 统一替换为 /fw/photo/ 请求
        location_url = location_url.replace("/fw/long-video/", "/fw/photo/")

        async with httpx.AsyncClient(headers=self.ios_headers, timeout=self.timeout) as client:
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

        return self.build_result(photo.parse_data)


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
            return []
        cdn = random.choice(self.cdn_list).cdn
        return [f"https://{cdn}/{url}" for url in self.img_route_list]


class ExtParams(Struct):
    atlas: Atlas = field(default_factory=Atlas)


class Photo(Struct):
    # 标题
    caption: str
    timestamp: int
    duration: int = 0
    user_name: str = field(default="未知用户", name="userName")
    head_url: str | None = field(default=None, name="headUrl")
    cover_urls: list[CdnUrl] = field(name="coverUrls", default_factory=list)
    main_mv_urls: list[CdnUrl] = field(name="mainMvUrls", default_factory=list)
    ext_params: ExtParams = field(name="ext_params", default_factory=ExtParams)

    @property
    def name(self) -> str:
        return self.user_name.replace("\u3164", "").strip()

    @property
    def cover_url(self):
        return random.choice(self.cover_urls).url if len(self.cover_urls) != 0 else None

    @property
    def video_url(self):
        return random.choice(self.main_mv_urls).url if len(self.main_mv_urls) != 0 else None

    @property
    def img_urls(self):
        return self.ext_params.atlas.img_urls

    @property
    def parse_data(self) -> ParseData:
        """转换为ParseData对象"""
        return ParseData(
            title=self.caption,
            name=self.name,
            avatar_url=self.head_url,
            timestamp=self.timestamp // 1000,  # 转换为秒
            images_urls=self.img_urls,
            video_url=self.video_url,
            cover_url=self.cover_url,
        )


class TusjohData(Struct):
    result: int
    photo: Photo | None = None


from typing import TypeAlias

KuaishouInitState: TypeAlias = dict[str, TusjohData]
