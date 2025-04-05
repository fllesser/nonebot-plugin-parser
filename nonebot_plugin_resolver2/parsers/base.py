from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import aiohttp


@dataclass
class VideoAuthor:
    """视频作者信息"""

    # 作者ID
    uid: str = ""

    # 作者昵称
    name: str = ""

    # 作者头像
    avatar: str = ""


@dataclass
class VideoInfo:
    """视频信息"""

    # 封面地址
    cover_url: str = ""

    # 视频标题
    title: str = ""

    # 音乐播放地址
    music_url: str = ""

    # 视频播放地址
    video_url: str = ""

    # 图集图片地址列表
    images: list[str] = field(default_factory=list)

    # 动态图片地址列表
    dynamic_images: list[str] = field(default_factory=list)

    # 作者信息
    author: VideoAuthor = field(default_factory=VideoAuthor)


class BaseParser(ABC):
    """解析器基类"""

    @property
    def default_headers(self) -> dict[str, str]:
        """默认请求头 ios 16.6"""
        return {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1 Edg/132.0.0.0"  # noqa: E501
        }

    @abstractmethod
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        """解析分享链接"""
        pass

    async def get_redirect_url(self, url: str) -> str:
        """获取重定向后的URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.default_headers, allow_redirects=False, ssl=False) as response:
                response.raise_for_status()
                return response.headers.get("Location", url)
