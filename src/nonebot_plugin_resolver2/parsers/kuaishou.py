import json
import re

import httpx

from ..constants import COMMON_HEADER, COMMON_TIMEOUT, IOS_HEADER
from ..exception import ParseException
from .data import ImageContent, ParseResult, VideoContent
from .utils import get_redirect_url


class KuaishouParser:
    """快手解析器"""

    def __init__(self):
        self.headers = COMMON_HEADER
        self.v_headers = {
            **IOS_HEADER,
            "Referer": "https://v.kuaishou.com/",
        }

    async def parse_url(self, url: str) -> ParseResult:
        """解析快手链接获取视频信息

        Args:
            url: 快手视频链接

        Returns:
            ParseResult: 快手视频信息
        """
        location_url = await get_redirect_url(url, headers=self.v_headers)

        if len(location_url) <= 0:
            raise ParseException("failed to get location url from url")

        # /fw/long-video/ 返回结果不一样, 统一替换为 /fw/photo/ 请求
        location_url = location_url.replace("/fw/long-video/", "/fw/photo/")

        async with httpx.AsyncClient(headers=self.v_headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(location_url)
            response.raise_for_status()
            response_text = response.text

            pattern = r"window\.INIT_STATE\s*=\s*(.*?)</script>"
            searched = re.search(pattern, response_text)

        if not searched or len(searched.groups()) < 1:
            raise ParseException("failed to parse video JSON info from HTML")

        json_text = searched.group(1).strip()
        try:
            json_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ParseException("failed to parse INIT_STATE payload") from e

        photo_data = {}
        for json_item in json_data.values():
            if "result" in json_item and "photo" in json_item:
                photo_data = json_item
                break

        if not photo_data:
            raise ParseException("failed to parse photo info from INIT_STATE")

        # 判断result状态
        if (result_code := photo_data["result"]) != 1:
            raise ParseException(f"获取作品信息失败: {result_code}")

        data = photo_data["photo"]

        # 获取视频地址
        video_content = None
        if "mainMvUrls" in data and len(data["mainMvUrls"]) > 0:
            video_url = data["mainMvUrls"][0]["url"]
            video_content = VideoContent(video_url=video_url)

        # 获取图集
        ext_params_atlas = data.get("ext_params", {}).get("atlas", {})
        atlas_cdn_list = ext_params_atlas.get("cdn", [])
        atlas_list = ext_params_atlas.get("list", [])
        images = []
        if len(atlas_cdn_list) > 0 and len(atlas_list) > 0:
            for atlas in atlas_list:
                images.append(f"https://{atlas_cdn_list[0]}/{atlas}")

        video_info = ParseResult(
            title=data["caption"],
            cover_url=data["coverUrls"][0]["url"],
            author=data["userName"],
            content=video_content or ImageContent(pic_urls=images),
        )
        return video_info

    async def _extract_video_id(self, url: str) -> str:
        """提取视频ID

        Args:
            url: 快手视频链接

        Returns:
            str: 视频ID
        """
        # 处理可能的短链接
        if "v.kuaishou.com" in url:
            url = await get_redirect_url(url)

        # 提取视频ID - 使用walrus operator和索引替代group()
        if "/fw/photo/" in url and (matched := re.search(r"/fw/photo/([^/?]+)", url)):
            return matched.group(1)
        elif "short-video" in url and (matched := re.search(r"short-video/([^/?]+)", url)):
            return matched.group(1)

        raise ParseException("无法从链接中提取视频ID")
