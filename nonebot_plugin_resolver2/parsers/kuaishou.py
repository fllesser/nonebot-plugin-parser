from dataclasses import dataclass
import re
import urllib.parse

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
        # 创建一个全局的ClientSession以重用
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建ClientSession

        Returns:
            aiohttp.ClientSession: 会话实例
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

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
        # URL编码content参数避免查询字符串无效
        encoded_url = urllib.parse.quote(standard_url)
        api_url = self.api_url.format(encoded_url)

        session = await self._get_session()
        if PROXY:
            async with session.get(api_url, headers=self.headers, proxy=PROXY) as resp:
                if resp.status != 200:
                    raise ParseException(f"解析API返回错误状态码: {resp.status}")

                result = await resp.json()

                # 根据API返回示例，成功时code应为0
                if result.get("code") != 0 or not result.get("data"):
                    raise ParseException(f"解析API返回错误: {result.get('msg', '未知错误')}")

                data = result["data"]
                return KuaishouVideoInfo(
                    # 字段名称与回退值
                    title=data.get("title", "未知标题"),
                    cover_url=data.get("imageUrl", ""),
                    video_url=data.get("url", ""),
                    # API可能不提供作者信息
                    author=data.get("name", ""),
                )
        else:
            async with session.get(api_url, headers=self.headers) as resp:
                if resp.status != 200:
                    raise ParseException(f"解析API返回错误状态码: {resp.status}")

                result = await resp.json()

                # 根据API返回示例，成功时code应为0
                if result.get("code") != 0 or not result.get("data"):
                    raise ParseException(f"解析API返回错误: {result.get('msg', '未知错误')}")

                data = result["data"]
                return KuaishouVideoInfo(
                    # 字段名称与回退值
                    title=data.get("title", "未知标题"),
                    cover_url=data.get("imageUrl", ""),
                    video_url=data.get("url", ""),
                    # API可能不提供作者信息
                    author=data.get("name", ""),
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

        # 提取视频ID - 使用walrus operator和索引替代group()
        if "/fw/photo/" in url and (match := re.search(r"/fw/photo/([^/?]+)", url)):
            return match[1]
        elif "short-video" in url and (match := re.search(r"short-video/([^/?]+)", url)):
            return match[1]

        raise ParseException("无法从链接中提取视频ID")

    async def _resolve_short_url(self, url: str) -> str:
        """解析短链接

        Args:
            url: 快手短链接

        Returns:
            str: 真实链接
        """
        session = await self._get_session()
        async with session.head(url, headers=self.headers, allow_redirects=True) as resp:
            # 验证响应状态码，确保请求成功
            if not 200 <= resp.status < 300:
                raise ParseException(f"解析短链接失败，状态码: {resp.status}")
            
            if not resp.real_url:
                raise ParseException("解析短链接失败，未获取到真实URL")
                
            return str(resp.real_url)

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
