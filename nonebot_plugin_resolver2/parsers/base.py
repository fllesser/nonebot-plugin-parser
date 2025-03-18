from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import aiohttp


@dataclass
class VideoAuthor:
    """
    视频作者信息
    """

    # 作者ID
    uid: str = ""

    # 作者昵称
    name: str = ""

    # 作者头像
    avatar: str = ""


@dataclass
class VideoInfo:
    """
    视频信息
    """

    # 封面地址
    cover_url: str = ""  # 封面地址

    title: str = ""  # 视频标题

    music_url: str = ""  # 音乐播放地址

    video_url: str = ""  # 视频播放地址

    # 图集图片地址列表
    images: list[str] = field(default_factory=list)

    dynamic_images: list[str] = field(default_factory=list)

    # 作者信息
    author: VideoAuthor = field(default_factory=VideoAuthor)


class BaseParser(ABC):
    @property
    def default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1 Edg/132.0.0.0"  # noqa: E501
        }

    @abstractmethod
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        """
        解析分享链接
        :param share_url: 分享链接
        :return: VideoInfo
        """
        pass

    @abstractmethod
    async def parse_video_id(self, video_id: str) -> VideoInfo:
        """
        :param video_id: 视频ID
        :return: VideoInfo
        """
        pass

    async def get_redirect_url(self, url: str) -> str:
        """
        获取重定向后的URL
        :param url: 原始URL
        :return: 重定向后的URL
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.default_headers, allow_redirects=False, ssl=False) as response:
                response.raise_for_status()
                return response.headers.get("Location", url)


class ParseException(Exception):
    """
    解析器异常
    """

    pass
