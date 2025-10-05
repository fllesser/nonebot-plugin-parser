import re
from typing import ClassVar
from typing_extensions import override

import httpx
import msgspec

from ..config import pconfig
from ..download import DOWNLOADER, YTDLP_DOWNLOADER
from .base import BaseParser
from .cookie import save_cookies_with_netscape
from .data import AudioContent, Author, ImageContent, ParseResult, Platform, VideoContent


class YouTubeParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="youtube", display_name="油管")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("youtube.com", r"https?://(?:www\.)?youtube\.com/(?:watch|shorts)(?:/[A-Za-z\d_\-]+|\?v=[A-Za-z\d_\-]+)"),
        ("youtu.be", r"https?://(?:www\.)?youtu\.be/[A-Za-z\d\._\?%&\+\-=/#]+"),
    ]

    def __init__(self):
        super().__init__()
        self.cookies_file = pconfig.config_dir / "ytb_cookies.txt"
        if pconfig.ytb_ck:
            save_cookies_with_netscape(pconfig.ytb_ck, self.cookies_file, "youtube.com")

    @override
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

        video_info = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
        author = await self._fetch_author_info(video_info.channel_id)
        cover = DOWNLOADER.download_img(video_info.thumbnail)
        contents = []
        if video_info.duration <= pconfig.duration_maximum:
            video = YTDLP_DOWNLOADER.download_video(url, self.cookies_file)
            contents.append(VideoContent(video, cover, duration=video_info.duration))
        else:
            contents.append(ImageContent(cover))

        return self.result(
            title=video_info.title,
            author=author,
            contents=contents,
            timestamp=video_info.timestamp,
        )

    async def parse_url_as_audio(self, url: str) -> ParseResult:
        """解析 YouTube URL 并标记为音频下载

        Args:
            url: YouTube 链接

        Returns:
            ParseResult: 解析结果（音频内容）

        """
        video_info = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
        author = await self._fetch_author_info(video_info.channel_id)

        contents = []
        contents.append(ImageContent(DOWNLOADER.download_img(video_info.thumbnail)))

        if video_info.duration <= pconfig.duration_maximum:
            audio_task = YTDLP_DOWNLOADER.download_audio(url, self.cookies_file)
            contents.append(AudioContent(audio_task, duration=video_info.duration))

        return self.result(
            title=video_info.title,
            author=author,
            contents=contents,
            timestamp=video_info.timestamp,
        )

    async def _fetch_author_info(self, channel_id: str):
        url = "https://www.youtube.com/youtubei/v1/browse?prettyPrint=false"
        payload = {
            "context": {
                "client": {
                    "hl": "zh-HK",
                    "gl": "US",
                    "deviceMake": "Apple",
                    "deviceModel": "",
                    "clientName": "WEB",
                    "clientVersion": "2.20251002.00.00",
                    "osName": "Macintosh",
                    "osVersion": "10_15_7",
                },
                "user": {"lockedSafetyMode": False},
                "request": {"useSsl": True, "internalExperimentFlags": [], "consistencyTokenJars": []},
            },
            "browseId": channel_id,
        }
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        browse_response = msgspec.json.decode(response.content, type=BrowseResponse)
        return browse_response.convert_to_author()


from msgspec import Struct


class Thumbnail(Struct):
    url: str


class AvatarInfo(Struct):
    thumbnails: list[Thumbnail]


class ChannelMetadataRenderer(Struct):
    title: str
    description: str
    avatar: AvatarInfo


class Metadata(Struct):
    channelMetadataRenderer: ChannelMetadataRenderer


class Avatar(Struct):
    thumbnails: list[Thumbnail]


class BrowseResponse(Struct):
    metadata: Metadata

    def convert_to_author(self) -> Author:
        channel_metadata = self.metadata.channelMetadataRenderer
        thumbnails = channel_metadata.avatar.thumbnails
        avatar = DOWNLOADER.download_img(thumbnails[0].url) if thumbnails else None
        return Author(
            name=channel_metadata.title,
            avatar=avatar,
            description=channel_metadata.description,
        )
