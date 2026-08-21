import re
import json
from typing import ClassVar

from httpx import AsyncClient

from ..base import (
    COMMON_TIMEOUT,
    Platform,
    BaseParser,
    PlatformEnum,
    ParseException,
    handle,
)
from .aweme import decoder


class DouyinParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.DOUYIN, display_name="抖音")

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Origin": "https://open.douyin.com",
                "Referer": "https://open.douyin.com/",
            }
        )

    # https://v.douyin.com/_2ljF4AmKL8
    @handle("v.douyin", r"v\.douyin\.com/[a-zA-Z0-9_\-]+")
    @handle("jx.douyin", r"jx\.douyin\.com/[a-zA-Z0-9_\-]+")
    async def _parse_short_link(self, searched: re.Match[str]):
        url = f"https://{searched.group(0)}"
        return await self.parse_with_redirect(url)

    # https://www.douyin.com/video/7521023890996514083
    # https://www.douyin.com/note/7469411074119322899
    @handle("douyin", r"douyin\.com/[a-z]+/(?P<aweme_id>\d+)")
    @handle("iesdouyin", r"iesdouyin\.com/share/[a-z]+/(?P<aweme_id>\d+)")
    @handle("m.douyin", r"m\.douyin\.com/share/[a-z]+/(?P<aweme_id>\d+)")
    # https://jingxuan.douyin.com/m/video/7574300896016862490?app=yumme&utm_source=copy_link
    @handle("jingxuan.douyin", r"jingxuan\.douyin.com/m/[a-z]+/(?P<aweme_id>\d+)")
    async def _parse_douyin(self, searched: re.Match[str]):
        aweme_id = searched.group("aweme_id")
        return await self.parse_aweme(aweme_id)

    async def parse_aweme(self, aweme_id: str):
        async with AsyncClient(
            headers=self.headers,
            timeout=COMMON_TIMEOUT,
            follow_redirects=True,
            verify=False,
        ) as client:
            response = await client.get(
                "https://www.douyin.com/aweme/v1/web/aweme/detail/",
                params={"aweme_id": aweme_id, "aid": "6383"},
            )
            if response.status_code != 200:
                raise ParseException(f"status: {response.status_code}")
            aweme = decoder.decode(response.content).aweme_detail

        # 作者
        author = self.create_author(
            aweme.author.nickname,
            aweme.author.avatar_thumb.url_list[-1],
            aweme.author.signature,
        )

        # 先以部分数据构建结果，后续再填充内容，避免使用临时变量
        result = self.result(
            text=aweme.share_info.text,
            author=author,
            timestamp=aweme.create_time,
            url=aweme.share_url.split("?")[0],
        )
        if music := aweme.music:
            if not music.is_original_sound:
                if music.play_url.uri == "":
                    extra = json.loads(music.extra)
                    music_url = extra.get("original_song_url")
                else:
                    music_url = music.play_url.uri
                if music_url:
                    result.contents.append(
                        self.create_audio(
                            url_or_task=music_url,
                            duration=music.duration,
                        )
                    )

        # 添加图片内容
        if images := aweme.images:
            for image in images:
                if image.clip_type == 2 or image.clip_type is None:
                    result.contents.append(
                        self.create_image(
                            url_or_task=image.url_list[-1],
                        )
                    )
                elif image_video := image.video:
                    result.contents.extend(
                        [
                            self.create_image(
                                url_or_task=image_video.cover.url_list[-1],
                            ),
                            self.create_video(url_or_task=image_video.play_addr.url),
                        ]
                    )
        # 添加视频内容
        elif video := aweme.video:
            result.video = self.create_video(
                video.play_addr.url,
                video.cover_original_scale.url_list[-1] if video.cover_original_scale else video.cover.url_list[-1],
                video.duration // 1000,
            )

        return result
