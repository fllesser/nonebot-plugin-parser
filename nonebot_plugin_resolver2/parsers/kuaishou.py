from dataclasses import dataclass
import re

import aiohttp

from ..config import PROXY
from ..exception import ParseException


@dataclass
class KuaishouVideoInfo:
    """快手视频信息"""

    title: str
    cover_url: str
    video_url: str
    author: str = ""


class KuaishouParser:
    """快手解析器"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        # 通用第三方解析API
        self.api_url = "http://47.99.158.118/video-crack/v2/parse?content={}"

    async def parse_url(self, url: str) -> KuaishouVideoInfo:
        """解析快手链接获取视频信息

        Args:
            url: 快手视频链接

        Returns:
            KuaishouVideoInfo: 快手视频信息
        """
        video_id = await self._extract_video_id(url)
        if not video_id:
            raise ParseException("无法从链接中提取视频ID")

        # 构造标准链接格式，用于API解析
        standard_url = f"https://www.kuaishou.com/short-video/{video_id}"
        api_url = self.api_url.format(standard_url)

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=self.headers, proxy=PROXY) as resp:
                if resp.status != 200:
                    raise ParseException(f"解析API返回错误状态码: {resp.status}")

                result = await resp.json()

                if result.get("code") != 200 or not result.get("data"):
                    raise ParseException(f"解析API返回错误: {result.get('msg', '未知错误')}")

                data = result["data"]
                return KuaishouVideoInfo(
                    title=data.get("desc", "未知标题"),
                    cover_url=data.get("cover", ""),
                    video_url=data.get("url", ""),
                    author=data.get("author", ""),
                )

    async def _extract_video_id(self, url: str) -> str:
        """提取视频ID

        Args:
            url: 快手视频链接

        Returns:
            str: 视频ID
        """
        # 处理可能的短链接
        if "v.kuaishou.com" in url:
            url = await self._resolve_short_url(url)

        # 提取视频ID
        if "/fw/photo/" in url:
            video_id_match = re.search(r"/fw/photo/([^/?]+)", url)
            if video_id_match:
                return video_id_match.group(1)
        elif "short-video" in url:
            video_id_match = re.search(r"short-video/([^/?]+)", url)
            if video_id_match:
                return video_id_match.group(1)

        raise ParseException("无法从链接中提取视频ID")

    async def _resolve_short_url(self, url: str) -> str:
        """解析短链接

        Args:
            url: 快手短链接

        Returns:
            str: 真实链接
        """
        async with aiohttp.ClientSession() as session:
            async with session.head(url, headers=self.headers, allow_redirects=True) as resp:
                return str(resp.real_url)
