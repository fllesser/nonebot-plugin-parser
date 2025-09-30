import json
import re
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

import httpx
import msgspec

from ..config import rconfig
from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..exception import ParseException
from .base import BaseParser
from .data import ImageContent, ParseResult, VideoContent
from .utils import get_redirect_url


class XiaoHongShuParser(BaseParser):
    # 平台名称（用于配置禁用和内部标识）
    platform_name: ClassVar[str] = "xiaohongshu"

    # 平台显示名称
    platform_display_name: ClassVar[str] = "小红书"

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("xiaohongshu.com", r"https?://(?:www\.)?xiaohongshu\.com/[A-Za-z0-9._?%&+=/#@-]*"),
        ("xhslink.com", r"https?://xhslink\.com/[A-Za-z0-9._?%&+=/#@-]*"),
    ]

    def __init__(self):
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.9",
            **COMMON_HEADER,
        }
        if rconfig.r_xhs_ck:
            self.headers["cookie"] = rconfig.r_xhs_ck

    async def parse_url(self, url: str) -> ParseResult:
        """解析小红书 URL

        Args:
            url (str): 小红书 URL

        Returns:
            ParseResult: 解析结果

        Raises:
            ParseException: 小红书分享链接不完整
            ParseException: 小红书 cookie 可能已失效
        """
        # 处理 xhslink 短链
        if "xhslink" in url:
            url = await get_redirect_url(url, self.headers)
        # ?: 非捕获组
        pattern = r"(?:/explore/|/discovery/item/|source=note&noteId=)(\w+)"
        matched = re.search(pattern, url)
        if not matched:
            raise ParseException("小红书分享链接不完整")
        xhs_id = matched.group(1)
        # 解析 URL 参数
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        # 提取 xsec_source 和 xsec_token
        xsec_source = params.get("xsec_source", [None])[0] or "pc_feed"
        xsec_token = params.get("xsec_token", [None])[0]

        # 构造完整 URL
        url = f"https://www.xiaohongshu.com/explore/{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}"
        async with httpx.AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            html = response.text

        pattern = r"window.__INITIAL_STATE__=(.*?)</script>"
        matched = re.search(pattern, html)
        if not matched:
            raise ParseException("小红书分享链接失效或内容已删除")

        json_str = matched.group(1)
        json_str = json_str.replace("undefined", "null")

        json_obj = json.loads(json_str)

        note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
        note_detail = msgspec.convert(note_data, type=NoteDetail)

        if video_url := note_detail.video_url:
            content = VideoContent(video_url=video_url)
            cover_url = note_detail.img_urls[0]
        else:
            content = ImageContent(pic_urls=note_detail.img_urls)
            cover_url = None

        return ParseResult(
            title=note_detail.title_desc,
            platform=self.platform_display_name,
            cover_url=cover_url,
            content=content,
            author=note_detail.user.nickname,
        )


from msgspec import Struct, field


class Image(Struct):
    urlDefault: str


class Stream(Struct):
    h264: list[dict] | None = None
    h265: list[dict] | None = None
    av1: list[dict] | None = None
    h266: list[dict] | None = None


class Media(Struct):
    stream: Stream


class Video(Struct):
    media: Media


class User(Struct):
    nickname: str


class NoteDetail(Struct):
    type: str
    title: str
    desc: str
    user: User
    imageList: list[Image] = field(default_factory=list)
    video: Video | None = None

    @property
    def title_desc(self) -> str:
        return f"{self.title}\n{self.desc}".strip()

    @property
    def img_urls(self) -> list[str]:
        return [item.urlDefault for item in self.imageList]

    @property
    def video_url(self) -> str | None:
        if self.type != "video" or not self.video:
            return None
        stream = self.video.media.stream

        if stream.h264:
            return stream.h264[0]["masterUrl"]
        elif stream.h265:
            return stream.h265[0]["masterUrl"]
        elif stream.av1:
            return stream.av1[0]["masterUrl"]
        elif stream.h266:
            return stream.h266[0]["masterUrl"]
        return None
