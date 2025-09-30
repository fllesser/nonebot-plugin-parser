import re
from typing import ClassVar

from nonebot import logger

from ..download.ytdlp import get_video_info
from ..exception import ParseException
from .base import BaseParser
from .data import ParseResult, VideoContent
from .utils import get_redirect_url


class TikTokParser(BaseParser):
    # 平台名称（用于配置禁用和内部标识）
    platform_name: ClassVar[str] = "tiktok"

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("tiktok.com", r"(?:https?://)?(www|vt|vm)\.tiktok\.com/[A-Za-z0-9._?%&+\-=/#@]*"),
    ]

    def __init__(self):
        self.platform = "TikTok"

    async def parse_url(self, url: str) -> ParseResult:
        """解析 TikTok URL（标准接口）

        Args:
            url: TikTok 链接

        Returns:
            ParseResult: 解析结果（仅包含 URL，不下载）

        Raises:
            ParseException: 解析失败
        """
        try:
            # 处理短链接重定向
            final_url = url
            if match := re.match(r"(?:https?://)?(?:www\.)?(vt|vm)\.tiktok\.com", url):
                prefix = match.group(1)
                if prefix in ("vt", "vm"):
                    try:
                        final_url = await get_redirect_url(url)
                        if not final_url:
                            raise ParseException("TikTok 短链重定向失败")
                    except Exception as e:
                        logger.exception(f"TikTok 短链重定向失败 | {url}")
                        raise ParseException(f"TikTok 短链重定向失败: {e}")

            # 获取视频信息
            info_dict = await get_video_info(final_url)
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
                platform=self.platform,
                author=author,
                cover_url=thumbnail,
                content=VideoContent(video_url=final_url),  # 保存重定向后的 URL
                extra_info=extra_info,
            )
        except ParseException:
            raise
        except Exception as e:
            logger.exception(f"TikTok 视频信息获取失败 | {url}")
            raise ParseException(f"TikTok 视频信息获取失败: {e}")
