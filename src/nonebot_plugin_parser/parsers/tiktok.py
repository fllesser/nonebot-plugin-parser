import re
from typing import ClassVar

from .base import BaseParser, PlatformEnum, handle
from .data import Author, Platform, VideoContent
from ..download import DOWNLOADER, YTDLP_DOWNLOADER


class TikTokParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.TIKTOK, display_name="TikTok")

    @handle("tiktok.com", r"(?:https?://)?(www|vt|vm)\.tiktok\.com/[A-Za-z0-9._?%&+\-=/#@]*")
    async def _parse(self, searched: re.Match[str]):
        # 从匹配对象中获取原始URL
        url, prefix = searched.group(0), searched.group(1)

        if prefix in ("vt", "vm"):
            url = await self.get_redirect_url(url)

        # 获取视频信息
        video_info = await YTDLP_DOWNLOADER.extract_video_info(url)

        # 下载封面和视频
        cover = DOWNLOADER.download_img(video_info.thumbnail)
        video = YTDLP_DOWNLOADER.download_video(url)

        return self.result(
            title=video_info.title,
            author=Author(name=video_info.channel),
            contents=[VideoContent(video, cover, duration=video_info.duration)],
            timestamp=video_info.timestamp,
        )
