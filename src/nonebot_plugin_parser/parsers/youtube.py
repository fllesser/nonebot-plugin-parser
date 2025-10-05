import re
from typing import ClassVar
from typing_extensions import override

from ..config import pconfig
from ..download import DOWNLOADER, YTDLP_DOWNLOADER
from .base import BaseParser
from .cookie import save_cookies_with_netscape
from .data import AudioContent, Author, ParseResult, Platform, VideoContent


class YouTubeParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="youtube", display_name="油管")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("youtube.com", r"https?://(?:www\.)?youtube\.com/[A-Za-z\d\._\?%&\+\-=/#]+"),
        ("youtu.be", r"https?://(?:www\.)?youtu\.be/[A-Za-z\d\._\?%&\+\-=/#]+"),
    ]

    def __init__(self):
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

        info_dict = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
        title = info_dict.get("title", "未知")
        author = info_dict.get("uploader", None)
        thumbnail = info_dict.get("thumbnail", None)
        duration = int(info_dict.get("duration", 0))

        cover = DOWNLOADER.download_img(thumbnail) if thumbnail else None
        video = YTDLP_DOWNLOADER.download_video(url, self.cookies_file)

        return self.result(
            title=title,
            author=Author(name=author) if author else None,
            contents=[VideoContent(video, cover, duration)],
        )

    async def parse_url_as_audio(self, url: str) -> ParseResult:
        """解析 YouTube URL 并标记为音频下载

        Args:
            url: YouTube 链接

        Returns:
            ParseResult: 解析结果（音频内容）

        """
        info_dict = await YTDLP_DOWNLOADER.extract_video_info(url, self.cookies_file)
        title = info_dict.get("title", "未知")
        author = info_dict.get("uploader", None)
        duration = int(info_dict.get("duration", 0))

        audio_path = YTDLP_DOWNLOADER.download_audio(url, self.cookies_file)

        return self.result(
            title=title,
            author=Author(name=author) if author else None,
            contents=[AudioContent(audio_path, duration)],
        )
