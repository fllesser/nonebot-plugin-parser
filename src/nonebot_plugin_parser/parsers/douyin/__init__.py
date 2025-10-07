import re
from typing import ClassVar
from typing_extensions import override

import httpx
import msgspec
from nonebot import logger

from ...constants import COMMON_TIMEOUT
from ...exception import ParseException
from ..base import BaseParser, Platform


class DouyinParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="douyin", display_name="抖音")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("v.douyin", r"https://v\.douyin\.com/[a-zA-Z0-9_\-]+"),
        (
            "douyin",
            r"https://www\.(?:douyin|iesdouyin)\.com/(?:video|note|share/(?:video|note|slides))/[0-9]+",
        ),
    ]

    def _build_iesdouyin_url(self, _type: str, video_id: str) -> str:
        return f"https://www.iesdouyin.com/share/{_type}/{video_id}"

    def _build_m_douyin_url(self, _type: str, video_id: str) -> str:
        return f"https://m.douyin.com/share/{_type}/{video_id}"

    async def parse_share_url(self, share_url: str):
        if matched := re.match(r"(video|note)/([0-9]+)", share_url):
            # https://www.douyin.com/video/xxxxxx
            _type, video_id = matched.group(1), matched.group(2)
            iesdouyin_url = self._build_iesdouyin_url(_type, video_id)
        else:
            # https://v.douyin.com/xxxxxx
            iesdouyin_url = await self.get_redirect_url(share_url)
            # https://www.iesdouyin.com/share/video/7468908569061100857/?region=CN&mid=0&u_
            matched = re.search(r"(slides|video|note)/(\d+)", iesdouyin_url)
            if not matched:
                raise ParseException(f"无法从 {share_url} 中解析出 ID")
            _type, video_id = matched.group(1), matched.group(2)
            if _type == "slides":
                return await self.parse_slides(video_id)
        for url in [
            self._build_m_douyin_url(_type, video_id),
            share_url,
            iesdouyin_url,
        ]:
            try:
                return await self.parse_video(url)
            except ParseException as e:
                logger.warning(f"failed to parse {url[:60]}, error: {e}")
                continue
        raise ParseException("分享已删除或资源直链获取失败, 请稍后再试")

    async def parse_video(self, url: str):
        async with httpx.AsyncClient(
            headers=self.ios_headers,
            timeout=COMMON_TIMEOUT,
            follow_redirects=False,
            verify=False,
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise ParseException(f"status: {response.status_code}")
            text = response.text

        pattern = re.compile(
            pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        matched = pattern.search(text)

        if not matched or not matched.group(1):
            raise ParseException("can't find _ROUTER_DATA in html")

        from .video import RouterData

        video_data = msgspec.json.decode(matched.group(1).strip(), type=RouterData).video_data

        # 使用新的简洁构建方式
        contents = []

        # 添加视频内容
        if video_url := video_data.video_url:
            cover_url = video_data.cover_url
            duration = video_data.video.duration if video_data.video else 0
            contents.append(self.create_video_content(video_url, cover_url, duration))

        # 添加图片内容
        if image_urls := video_data.image_urls:
            contents.extend(self.create_image_contents(image_urls))

        # 构建作者
        author = self.create_author(video_data.author.nickname, video_data.avatar_url)

        return self.result(
            title=video_data.desc,
            author=author,
            contents=contents,
            timestamp=video_data.create_time,
        )

    async def parse_slides(self, video_id: str):
        url = "https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/"
        params = {
            "aweme_ids": f"[{video_id}]",
            "request_source": "200",
        }
        async with httpx.AsyncClient(headers=self.android_headers, verify=False) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        from .slides import SlidesInfo

        slides_data = msgspec.json.decode(response.content, type=SlidesInfo).aweme_details[0]
        # 使用新的简洁构建方式
        contents = []

        # 添加图片内容
        if image_urls := slides_data.image_urls:
            contents.extend(self.create_image_contents(image_urls))

        # 添加动态内容
        if dynamic_urls := slides_data.dynamic_urls:
            contents.extend(self.create_dynamic_contents(dynamic_urls))

        # 构建作者
        author = self.create_author(slides_data.name, slides_data.avatar_url)

        return self.result(
            title=slides_data.desc,
            author=author,
            contents=contents,
            timestamp=slides_data.create_time,
        )

    @override
    async def parse(self, matched: re.Match[str]):
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path)

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        url = matched.group(0)
        return await self.parse_share_url(url)
