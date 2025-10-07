import json
import re
from typing import ClassVar
from typing_extensions import override
from urllib.parse import parse_qs, urlparse

import httpx
import msgspec

from ..exception import ParseException
from .base import BaseParser, Platform


class XiaoHongShuParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="xiaohongshu", display_name="小红书")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("xiaohongshu.com", r"https?://(?:www\.)?xiaohongshu\.com/[A-Za-z0-9._?%&+=/#@-]*"),
        ("xhslink.com", r"https?://xhslink\.com/[A-Za-z0-9._?%&+=/#@-]*"),
    ]

    def __init__(self):
        super().__init__()
        extra_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.9",
        }
        self.headers.update(extra_headers)

    @override
    async def parse(self, matched: re.Match[str]):
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        url = matched.group(0)
        # 处理 xhslink 短链
        if "xhslink" in url:
            url = await self.get_redirect_url(url, self.headers)
        # ?: 非捕获组
        pattern = r"(?:/explore/|/discovery/item/|source=note&noteId=)(\w+)"
        match_result = re.search(pattern, url)
        if not match_result:
            raise ParseException("小红书分享链接不完整")
        xhs_id = match_result.group(1)
        # 解析 URL 参数
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        # 提取 xsec_source 和 xsec_token
        xsec_source = params.get("xsec_source", [None])[0] or "pc_feed"
        xsec_token = params.get("xsec_token", [None])[0]

        # 构造完整 URL
        url = f"https://www.xiaohongshu.com/explore/{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}"
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.get(url)
            html = response.text

        pattern = r"window.__INITIAL_STATE__=(.*?)</script>"
        match_result = re.search(pattern, html)
        if not match_result:
            raise ParseException("小红书分享链接失效或内容已删除")

        json_str = match_result.group(1)
        json_str = json_str.replace("undefined", "null")

        json_obj = json.loads(json_str)

        note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
        note_detail = msgspec.convert(note_data, type=NoteDetail)

        # 使用新的简洁构建方式
        contents = []

        # 添加视频内容
        if video_url := note_detail.video_url:
            # 使用第一张图片作为封面
            cover_url = note_detail.image_urls[0] if note_detail.image_urls else None
            contents.append(self.create_video_content(video_url, cover_url))

        # 添加图片内容
        elif image_urls := note_detail.image_urls:
            contents.extend(self.create_image_contents(image_urls))

        # 构建作者
        author = self.create_author(note_detail.nickname, note_detail.avatar_url)

        return self.result(
            title=note_detail.title_desc,
            author=author,
            contents=contents,
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
    avatar: str


class NoteDetail(Struct):
    type: str
    title: str
    desc: str
    user: User
    imageList: list[Image] = field(default_factory=list)
    video: Video | None = None

    @property
    def nickname(self) -> str:
        return self.user.nickname

    @property
    def avatar_url(self) -> str:
        return self.user.avatar

    @property
    def title_desc(self) -> str:
        return f"{self.title}\n{self.desc}".strip()

    @property
    def image_urls(self) -> list[str]:
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
