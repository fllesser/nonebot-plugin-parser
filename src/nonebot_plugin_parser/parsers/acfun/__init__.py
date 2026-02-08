import re
from typing import ClassVar

from httpx import AsyncClient
from nonebot import logger

from ..base import (
    COMMON_TIMEOUT,
    Platform,
    BaseParser,
    PlatformEnum,
    ParseException,
    IgnoreException,
    handle,
    pconfig,
)


class AcfunParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.ACFUN, display_name="猴山")

    def __init__(self):
        super().__init__()
        self.headers["referer"] = "https://www.acfun.cn/"

    @handle("acfun.cn", r"(?:ac=|/ac)(?P<acid>\d+)")
    async def _parse(self, searched: re.Match[str]):
        acid = int(searched.group("acid"))
        url = f"https://www.acfun.cn/v/ac{acid}"

        video_info = await self.parse_video_info(url)
        author = self.create_author(video_info.name, video_info.avatar_url)

        if (duration := video_info.duration) >= pconfig.duration_maximum:
            logger.warning(f"视频时长 {duration} 超过最大限制 {pconfig.duration_maximum}")
            raise IgnoreException

        video_task = self.downloader.download_m3u8(
            video_info.m3u8_url,
            video_name=f"acfun_{acid}.mp4",
        )

        video_content = self.create_video_content(video_task, cover_url=video_info.coverUrl)

        return self.result(
            title=video_info.title,
            text=video_info.text,
            author=author,
            timestamp=video_info.timestamp,
            contents=[video_content],
        )

    async def parse_video_info(self, url: str):
        """解析 acfun 视频信息"""
        from . import video

        # 拼接查询参数
        url = f"{url}?quickViewId=videoInfo_new&ajaxpipe=1"

        async with AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw = response.text

        matched = re.search(r"window\.videoInfo =(.*?)</script>", raw)
        if not matched:
            raise ParseException("解析 acfun 视频信息失败")

        raw = str(matched.group(1))
        raw = re.sub(r'\\{1,4}"', '"', raw)
        raw = raw.replace('"{', "{").replace('}"', "}")
        return video.decoder.decode(raw)
