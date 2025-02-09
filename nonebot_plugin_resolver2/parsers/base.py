import aiohttp
import dataclasses
from abc import ABC, abstractmethod
from typing import Dict, List


@dataclasses.dataclass
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


@dataclasses.dataclass
class VideoInfo:
    """
    视频信息
    """

    # 视频播放地址
    video_url: str

    # 视频封面地址
    cover_url: str

    # 视频标题
    title: str = ""

    # 音乐播放地址
    music_url: str = ""

    # 图集图片地址列表
    images: List[str] = dataclasses.field(default_factory=list)

    dynamic_images: List[str] = dataclasses.field(default_factory=list)

    # 视频作者信息
    author: VideoAuthor = dataclasses.field(default_factory=VideoAuthor)


class BaseParser(ABC):
    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1 Edg/132.0.0.0"
        }

    @abstractmethod
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        """
        解析分享链接, 获取视频信息
        :param share_url: 视频分享链接
        :return: VideoInfo
        """
        pass

    @abstractmethod
    async def parse_video_id(self, video_id: str) -> VideoInfo:
        """
        解析视频ID, 获取视频信息
        :param video_id: 视频ID
        :return:
        """
        pass

    async def get_redirect_url(self, video_url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                video_url, headers=self.get_default_headers(), allow_redirects=False
            ) as response:
                # 返回重定向后的地址，如果没有重定向则返回原地址(抖音中的西瓜视频,重定向地址为空)
                return response.headers.get("Location", video_url)
