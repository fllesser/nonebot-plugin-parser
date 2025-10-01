import re
from typing import ClassVar

from nonebot import logger

from ..config import rconfig, ytb_cookies_file
from ..cookie import save_cookies_with_netscape
from ..download import DOWNLOADER, YTDLP_DOWNLOADER
from ..exception import ParseException
from .base import BaseParser
from .data import AudioContent, ParseResult, VideoContent


class YouTubeParser(BaseParser):
    # 平台名称（用于配置禁用和内部标识）
    platform_name: ClassVar[str] = "youtube"

    # 平台显示名称
    platform_display_name: ClassVar[str] = "油管"

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("youtube.com", r"https?://(?:www\.)?youtube\.com/[A-Za-z\d\._\?%&\+\-=/#]+"),
        ("youtu.be", r"https?://(?:www\.)?youtu\.be/[A-Za-z\d\._\?%&\+\-=/#]+"),
    ]

    def __init__(self):
        self.cookies_file = ytb_cookies_file
        if rconfig.r_ytb_ck:
            save_cookies_with_netscape(rconfig.r_ytb_ck, self.cookies_file, "youtube.com")

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
        try:
            info_dict = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
            title = info_dict.get("title", "未知")
            author = info_dict.get("uploader", None)
            thumbnail = info_dict.get("thumbnail", None)
            duration = info_dict.get("duration", None)

            # 构建额外信息
            extra_info_parts = []
            if duration and isinstance(duration, (int, float)):
                minutes = int(duration) // 60
                seconds = int(duration) % 60
                extra_info_parts.append(f"时长: {minutes}:{seconds:02d}")
            if extra_info_parts:
                extra_info = "\n".join(extra_info_parts)
            else:
                extra_info = None

            cover_path = None
            if thumbnail:
                cover_path = await DOWNLOADER.download_img(thumbnail)

            video_path = await YTDLP_DOWNLOADER.download_video(url, self.cookies_file)

            return ParseResult(
                title=title,
                platform=self.platform_display_name,
                author=author,
                cover_path=cover_path,
                content=VideoContent(video_path=video_path),
                extra_info=extra_info,
            )
        except Exception as e:
            logger.exception(f"YouTube 视频信息获取失败 | {url}")
            raise ParseException(f"YouTube 视频信息获取失败: {e}")

    async def parse_url_as_audio(self, url: str) -> ParseResult:
        """解析 YouTube URL 并标记为音频下载

        Args:
            url: YouTube 链接

        Returns:
            ParseResult: 解析结果（音频内容）

        Raises:
            ParseException: 解析失败
        """
        try:
            info_dict = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
            title = info_dict.get("title", "未知")
            author = info_dict.get("uploader", None)
            thumbnail = info_dict.get("thumbnail", None)
            duration = info_dict.get("duration", None)

            # 构建额外信息
            extra_info_parts = []
            if duration and isinstance(duration, (int, float)):
                minutes = int(duration) // 60
                seconds = int(duration) % 60
                extra_info_parts.append(f"时长: {minutes}:{seconds:02d}")
            if extra_info_parts:
                extra_info = "\n".join(extra_info_parts)
            else:
                extra_info = None

            cover_path = None
            if thumbnail:
                cover_path = await DOWNLOADER.download_img(thumbnail)

            audio_path = await YTDLP_DOWNLOADER.download_audio(url, self.cookies_file)

            return ParseResult(
                title=title,
                platform=self.platform_display_name,
                author=author,
                cover_path=cover_path,
                content=AudioContent(audio_path=audio_path),
                extra_info=extra_info,
            )
        except Exception as e:
            logger.exception(f"YouTube 音频信息获取失败 | {url}")
            raise ParseException(f"YouTube 音频信息获取失败: {e}")
