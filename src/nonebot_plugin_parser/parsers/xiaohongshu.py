import json
import re
from typing import Any, ClassVar
from typing_extensions import override
from urllib.parse import parse_qs

import httpx
import msgspec
from msgspec import Struct, field
from nonebot import logger

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
        explore_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.9",
        }
        self.headers.update(explore_headers)
        discovery_headers = {
            "origin": "https://www.xiaohongshu.com",
            "x-requested-with": "XMLHttpRequest",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        }
        self.ios_headers.update(discovery_headers)

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
        logger.debug(f"matched url: {url}")
        # 处理 xhslink 短链
        if "xhslink" in url:
            url = await self.get_redirect_url(url, self.headers)
            logger.debug(f"redirect url: {url}")
        # ?: 非捕获组
        pattern = r"(/explore/|/discovery/item/|source=note&noteId=)([a-zA-Z0-9]+)"
        searched = re.search(pattern, url)
        if not searched:
            raise ParseException("小红书分享链接不完整")

        route, xhs_id = searched.group(1), searched.group(2)
        if route == "/explore/":
            return await self._parse_explore(url, xhs_id)
        elif route == "/discovery/item/":
            return await self._parse_discovery(url)
        else:
            params = parse_qs(url)
            # 提取 xsec_source 和 xsec_token
            xsec_source = params.get("xsec_source", [None])[0] or "pc_feed"
            xsec_token = params.get("xsec_token", [None])[0]
            discovery_url = (
                f"https://www.xiaohongshu.com/discovery/item/{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}"
            )
            return await self._parse_discovery(discovery_url)

    async def _parse_explore(self, url: str, xhs_id: str):
        async with httpx.AsyncClient(
            timeout=self.timeout,
        ) as client:
            response = await client.get(url)
            html = response.text
            logger.info(f"url: {response.url} | status_code: {response.status_code}")

        json_obj = self._extract_initial_state_json(html)

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
            title=note_detail.title,
            text=note_detail.desc,
            author=author,
            contents=contents,
        )

    async def _parse_discovery(self, url: str):
        async with httpx.AsyncClient(
            headers=self.ios_headers,
            timeout=self.timeout,
            follow_redirects=True,
            cookies=httpx.Cookies(),
            trust_env=False,
        ) as client:
            response = await client.get(url)
            html = response.text

        json_obj = self._extract_initial_state_json(html)

        note_data = json_obj.get("noteData", {}).get("data", {}).get("noteData", {})
        if not note_data:
            raise ParseException("小红书分享链接失效或内容已删除")

        class Img(Struct):
            url: str

        class User(Struct):
            nickName: str
            avatar: str

        class NoteData(Struct):
            type: str
            title: str
            desc: str
            user: User
            time: int
            lastUpdateTime: int
            imageList: list[Img] = []
            video: Video | None = None

            @property
            def image_urls(self) -> list[str]:
                return [item.url for item in self.imageList]

            @property
            def video_url(self) -> str | None:
                if self.type != "video" or not self.video:
                    return None
                return self.video.video_url

        note_data = msgspec.convert(note_data, type=NoteData)

        contents = []
        if video_url := note_data.video_url:
            contents.append(self.create_video_content(video_url, note_data.image_urls[0]))
        elif img_urls := note_data.image_urls:
            contents.extend(self.create_image_contents(img_urls))

        return self.result(
            title=note_data.title,
            author=self.create_author(note_data.user.nickName, note_data.user.avatar),
            contents=contents,
            text=note_data.desc,
            timestamp=note_data.time // 1000,
        )

    def _extract_initial_state_json(self, html: str) -> dict[str, Any]:
        pattern = r"window\.__INITIAL_STATE__=(.*?)</script>"
        matched = re.search(pattern, html)
        if not matched:
            raise ParseException("小红书分享链接失效或内容已删除")

        json_str = matched.group(1).replace("undefined", "null")
        return json.loads(json_str)


class Image(Struct):
    urlDefault: str


class Stream(Struct):
    h264: list[dict[str, Any]] | None = None
    h265: list[dict[str, Any]] | None = None
    av1: list[dict[str, Any]] | None = None
    h266: list[dict[str, Any]] | None = None


class Media(Struct):
    stream: Stream


class Video(Struct):
    media: Media

    @property
    def video_url(self) -> str | None:
        stream = self.media.stream

        if stream.h264:
            return stream.h264[0]["masterUrl"]
        elif stream.h265:
            return stream.h265[0]["masterUrl"]
        elif stream.av1:
            return stream.av1[0]["masterUrl"]
        elif stream.h266:
            return stream.h266[0]["masterUrl"]
        return None


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
    def image_urls(self) -> list[str]:
        return [item.urlDefault for item in self.imageList]

    @property
    def video_url(self) -> str | None:
        if self.type != "video" or not self.video:
            return None
        return self.video.video_url
