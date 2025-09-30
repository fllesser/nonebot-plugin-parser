from typing import ClassVar

from nonebot import logger

from ..config import ytb_cookies_file
from ..download.ytdlp import get_video_info
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

    async def parse_url(self, url: str) -> ParseResult:
        """解析 YouTube URL（标准接口）

        Args:
            url: YouTube 链接

        Returns:
            ParseResult: 解析结果（仅包含 URL，不下载）

        Raises:
            ParseException: 解析失败
        """
        try:
            info_dict = await get_video_info(url, self.cookies_file)
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

            # YouTube 可以下载视频或音频，这里默认返回视频内容
            # 实际下载时会根据用户选择下载视频或音频
            return ParseResult(
                title=title,
                platform=self.platform_display_name,
                author=author,
                cover_url=thumbnail,
                content=VideoContent(video_url=url),  # 保存原始 URL，下载时使用
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
            info_dict = await get_video_info(url, self.cookies_file)
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

            return ParseResult(
                title=title,
                platform=self.platform_display_name,
                author=author,
                cover_url=thumbnail,
                content=AudioContent(audio_url=url),  # 保存原始 URL，下载时使用
                extra_info=extra_info,
            )
        except Exception as e:
            logger.exception(f"YouTube 音频信息获取失败 | {url}")
            raise ParseException(f"YouTube 音频信息获取失败: {e}")
