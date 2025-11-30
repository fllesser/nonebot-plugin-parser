import re
from typing import ClassVar

import msgspec
from httpx import AsyncClient

from .base import Platform, BaseParser, PlatformEnum, handle, pconfig
from .cookie import save_cookies_with_netscape
from ..download import YTDLP_DOWNLOADER


class YouTubeParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.YOUTUBE, display_name="油管")

    def __init__(self):
        super().__init__()
        self.cookies_file = pconfig.config_dir / "ytb_cookies.txt"
        if pconfig.ytb_ck:
            save_cookies_with_netscape(
                pconfig.ytb_ck,
                self.cookies_file,
                "youtube.com",
            )

    @handle("youtu.be", r"https?://(?:www\.)?youtu\.be/[A-Za-z\d\._\?%&\+\-=/#]+")
    @handle(
        "youtube.com",
        r"https?://(?:www\.)?youtube\.com/(?:watch|shorts)(?:/[A-Za-z\d_\-]+|\?v=[A-Za-z\d_\-]+)",
    )
    async def _parse_video(self, searched: re.Match[str]):
        return await self.parse_video(searched)

    async def parse_video(self, searched: re.Match[str]):
        # 从匹配对象中获取原始URL
        url = searched.group(0)

        video_info = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
        author = await self._fetch_author_info(video_info.channel_id)

        contents = []
        if video_info.duration <= pconfig.duration_maximum:
            video = YTDLP_DOWNLOADER.download_video(url, self.cookies_file)
            contents.append(
                self.create_video_content(
                    video,
                    video_info.thumbnail,
                    video_info.duration,
                )
            )
        else:
            contents.extend(self.create_image_contents([video_info.thumbnail]))

        return self.result(
            title=video_info.title,
            author=author,
            contents=contents,
            timestamp=video_info.timestamp,
        )

    async def parse_audio(self, url: str):
        """解析 YouTube URL 并标记为音频下载

        Args:
            url: YouTube 链接

        Returns:
            ParseResult: 解析结果（音频内容）

        """
        video_info = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
        author = await self._fetch_author_info(video_info.channel_id)

        contents = []
        contents.extend(self.create_image_contents([video_info.thumbnail]))

        if video_info.duration <= pconfig.duration_maximum:
            audio_task = YTDLP_DOWNLOADER.download_audio(url, self.cookies_file)
            contents.append(self.create_audio_content(audio_task, duration=video_info.duration))

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
                "request": {
                    "useSsl": True,
                    "internalExperimentFlags": [],
                    "consistencyTokenJars": [],
                },
            },
            "browseId": channel_id,
        }
        async with AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        browse = msgspec.json.decode(response.content, type=BrowseResponse)
        return self.create_author(browse.name, browse.avatar_url, browse.description)


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

    @property
    def name(self) -> str:
        return self.metadata.channelMetadataRenderer.title

    @property
    def avatar_url(self) -> str | None:
        thumbnails = self.metadata.channelMetadataRenderer.avatar.thumbnails
        return thumbnails[0].url if thumbnails else None

    @property
    def description(self) -> str:
        return self.metadata.channelMetadataRenderer.description
