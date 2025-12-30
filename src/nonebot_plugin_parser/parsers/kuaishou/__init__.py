import re
from typing import ClassVar

from httpx import AsyncClient

from ..base import BaseParser, PlatformEnum, ParseException, handle
from ..data import Platform


class KuaiShouParser(BaseParser):
    """快手解析器"""

    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.KUAISHOU, display_name="快手")

    def __init__(self):
        super().__init__()
        self.ios_headers["Referer"] = "https://v.kuaishou.com/"

    # https://v.kuaishou.com/2yAnzeZ
    @handle("v.kuaishou", r"v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+")
    # https://www.kuaishou.com/short-video/3xhjgcmir24m4nm
    @handle("kuaishou", r"(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+")
    # https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc
    @handle("chenzhongtech", r"(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+")
    async def _parse_v_kuaishou(self, searched: re.Match[str]):
        from . import states

        # 从匹配对象中获取原始URL
        url = f"https://{searched.group(0)}"
        real_url = await self.get_redirect_url(url, headers=self.ios_headers)

        if len(real_url) <= 0:
            raise ParseException("failed to get location url from url")

        # /fw/long-video/ 返回结果不一样, 统一替换为 /fw/photo/ 请求
        real_url = real_url.replace("/fw/long-video/", "/fw/photo/")

        async with AsyncClient(headers=self.ios_headers, timeout=self.timeout) as client:
            response = await client.get(real_url)
            response.raise_for_status()
            response_text = response.text

        pattern = r"window\.INIT_STATE\s*=\s*(.*?)</script>"
        matched = re.search(pattern, response_text)

        if not matched:
            raise ParseException("failed to parse video JSON info from HTML")

        raw = matched.group(1).strip()
        datas = states.decoder.decode(raw)

        photo = next((d.photo for d in datas.values() if d.photo is not None), None)
        if photo is None:
            raise ParseException("window.init_state don't contains videos or pics")

        # 简洁的构建方式
        contents = []

        # 添加视频内容
        if video_url := photo.video_url:
            contents.append(self.create_video_content(video_url, photo.cover_url, photo.duration))

        # 添加图片内容
        if img_urls := photo.img_urls:
            contents.extend(self.create_image_contents(img_urls))

        # 构建作者
        author = self.create_author(photo.name, photo.head_url)

        return self.result(
            title=photo.caption,
            author=author,
            contents=contents,
            timestamp=photo.timestamp // 1000,
        )
