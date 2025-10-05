"""Parser 基类定义"""

from abc import ABC, abstractmethod
import re
from typing import ClassVar
from typing_extensions import Unpack

import httpx

from ..constants import ANDROID_HEADER, COMMON_HEADER, COMMON_TIMEOUT, IOS_HEADER
from .data import ParseResult, ParseResultKwargs, Platform, TransitionData


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
    def result(cls, **kwargs: Unpack[ParseResultKwargs]) -> ParseResult:
        """构建解析结果"""
        return ParseResult(platform=cls.platform, **kwargs)

    @staticmethod
    async def get_redirect_url(url: str, headers: dict[str, str] | None = None) -> str:
        """获取重定向后的URL"""

        headers = headers or COMMON_HEADER.copy()
        async with httpx.AsyncClient(
            headers=headers, verify=False, follow_redirects=False, timeout=COMMON_TIMEOUT
        ) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                response.raise_for_status()
            return response.headers.get("Location", url)

    def convert_transition_to_result(self, data: TransitionData) -> ParseResult:
        """转换为解析结果"""
        from ..download import DOWNLOADER
        from .data import Author, DynamicContent, ImageContent, MediaContent, VideoContent

        # 填充作者信息
        name, avatar, desc = data.name_avatar_desc()
        if avatar is not None:
            avatar = DOWNLOADER.download_img(avatar)
        author = Author(name=name, avatar=avatar, description=desc)

        # 填充封面信息
        cover_task = None
        if cover_url := data.get_cover_url():
            cover_task = DOWNLOADER.download_img(cover_url, ext_headers=self.headers)

        # 填充内容信息
        contents: list[MediaContent] = []
        if images_urls := data.get_images_urls():
            img_tasks = [DOWNLOADER.download_img(url, ext_headers=self.headers) for url in images_urls]
            contents.extend(ImageContent(task) for task in img_tasks)
        if dynamic_urls := data.get_dynamic_urls():
            dynamic_tasks = [DOWNLOADER.download_video(url, ext_headers=self.headers) for url in dynamic_urls]
            contents.extend(DynamicContent(task) for task in dynamic_tasks)

        if video_url := data.get_video_url():
            video_task = DOWNLOADER.download_video(video_url, ext_headers=self.headers)
            contents.append(VideoContent(video_task, cover_task))
        else:
            if cover_task:
                contents.append(ImageContent(cover_task))

        return self.result(
            author=author,
            contents=contents,
            title=data.get_title(),
            text=data.get_text(),
            timestamp=data.get_timestamp(),
            url=data.get_url(),
            extra=data.get_extra(),
            repost=data.get_repost(),
        )
