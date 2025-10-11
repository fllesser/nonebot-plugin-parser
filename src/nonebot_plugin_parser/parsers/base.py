"""Parser 基类定义"""

from abc import ABC, abstractmethod
from asyncio import Task
from pathlib import Path
import re
from typing import ClassVar
from typing_extensions import Unpack

from ..constants import ANDROID_HEADER, COMMON_HEADER, COMMON_TIMEOUT, IOS_HEADER
from .data import ParseResult, ParseResultKwargs, Platform


class BaseParser(ABC):
    """所有平台 Parser 的抽象基类

    子类必须实现：
    - platform: 平台信息（包含名称和显示名称）
    - patterns: URL 正则表达式模式列表
    - parse: 解析 URL 的方法（接收正则表达式对象）
    """

    # 类变量：存储所有已注册的 Parser 类
    _registry: ClassVar[list[type["BaseParser"]]] = []

    platform: ClassVar[Platform]
    """ 平台信息（包含名称和显示名称） """

    patterns: ClassVar[list[tuple[str, str]]]
    """ URL 正则表达式模式列表 [(keyword, pattern), ...] """

    def __init__(self):
        self.headers = COMMON_HEADER.copy()
        self.ios_headers = IOS_HEADER.copy()
        self.android_headers = ANDROID_HEADER.copy()
        self.timeout = COMMON_TIMEOUT

    def __init_subclass__(cls, **kwargs):
        """自动注册子类到 _registry"""
        super().__init_subclass__(**kwargs)
        if ABC not in cls.__bases__:  # 跳过抽象类
            BaseParser._registry.append(cls)

    @classmethod
    def get_all_subclass(cls) -> list[type["BaseParser"]]:
        """获取所有已注册的 Parser 类"""
        return cls._registry

    @abstractmethod
    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        raise NotImplementedError

    @classmethod
    def search_url(cls, url: str) -> re.Match[str]:
        from nonebot import logger

        """搜索 URL 匹配模式"""
        for keyword, pattern in cls.patterns:
            if keyword not in url:
                continue
            if searched := re.search(pattern, url):
                return searched
            logger.debug(f"keyword '{keyword}' is in '{url}', but not matched")
        raise ValueError(f"无法匹配 {url}")

    @classmethod
    def result(cls, **kwargs: Unpack[ParseResultKwargs]) -> ParseResult:
        """构建解析结果"""
        return ParseResult(platform=cls.platform, **kwargs)

    @staticmethod
    async def get_redirect_url(url: str, headers: dict[str, str] | None = None) -> str:
        """获取重定向后的URL"""
        from httpx import AsyncClient

        headers = headers or COMMON_HEADER.copy()
        async with AsyncClient(headers=headers, verify=False, follow_redirects=False, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                response.raise_for_status()
            return response.headers.get("Location", url)

    def create_author(self, name: str, avatar_url: str | None = None, description: str | None = None):
        """创建作者对象"""
        from ..download import DOWNLOADER
        from .data import Author

        avatar_task = None
        if avatar_url:
            avatar_task = DOWNLOADER.download_img(avatar_url, ext_headers=self.headers)
        return Author(name=name, avatar=avatar_task, description=description)

    def create_video_content(self, url_or_task: str | Task[Path], cover_url: str | None = None, duration: float = 0.0):
        """创建视频内容"""
        from ..download import DOWNLOADER
        from .data import VideoContent

        cover_task = None
        if cover_url:
            cover_task = DOWNLOADER.download_img(cover_url, ext_headers=self.headers)
        if isinstance(url_or_task, str):
            url_or_task = DOWNLOADER.download_video(url_or_task, ext_headers=self.headers)

        return VideoContent(url_or_task, cover_task, duration)

    def create_image_contents(self, image_urls: list[str]):
        """创建图片内容列表"""
        from ..download import DOWNLOADER
        from .data import ImageContent

        img_tasks = [DOWNLOADER.download_img(url, ext_headers=self.headers) for url in image_urls]
        return [ImageContent(task) for task in img_tasks]

    def create_dynamic_contents(self, dynamic_urls: list[str]):
        """创建动态图片内容列表"""
        from ..download import DOWNLOADER
        from .data import DynamicContent

        dynamic_tasks = [DOWNLOADER.download_video(url, ext_headers=self.headers) for url in dynamic_urls]
        return [DynamicContent(task) for task in dynamic_tasks]

    def create_audio_content(self, url_or_task: str | Task[Path], duration: float = 0.0):
        """创建音频内容"""
        from ..download import DOWNLOADER
        from .data import AudioContent

        if isinstance(url_or_task, str):
            url_or_task = DOWNLOADER.download_audio(url_or_task, ext_headers=self.headers)

        return AudioContent(url_or_task, duration)

    def create_graphics_content(self, image_url: str, text: str | None = None, alt: str | None = None):
        """创建图文内容 图片不能为空 文字可空 渲染时文字在前 图片在后"""
        from ..download import DOWNLOADER
        from .data import GraphicsContent

        image_task = DOWNLOADER.download_img(image_url, ext_headers=self.headers)
        return GraphicsContent(image_task, text, alt)
