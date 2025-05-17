import json
import re
import urllib.parse

import aiohttp

from ..constant import COMMON_HEADER, IOS_HEADER
from ..exception import ParseException
from .data import ParseResult
from .utils import get_redirect_url


class KuaishouParser:
    """快手解析器"""

    def __init__(self):
        self.headers = COMMON_HEADER
        self.v_headers = {
            **IOS_HEADER,
            "Referer": "https://v.kuaishou.com/",
        }
        # 通用第三方解析API
        self.api_url = "http://47.99.158.118/video-crack/v2/parse?content={}"

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

        async with aiohttp.ClientSession() as session:
            async with session.get(location_url, headers=self.v_headers) as resp:
                resp.raise_for_status()
                response_text = await resp.text()

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
        video_url = ""
        if "mainMvUrls" in data and len(data["mainMvUrls"]) > 0:
            video_url = data["mainMvUrls"][0]["url"]

        # 获取图集
        ext_params_atlas = data.get("ext_params", {}).get("atlas", {})
        atlas_cdn_list = ext_params_atlas.get("cdn", [])
        atlas_list = ext_params_atlas.get("list", [])
        images = []
        if len(atlas_cdn_list) > 0 and len(atlas_list) > 0:
            for atlas in atlas_list:
                images.append(f"https://{atlas_cdn_list[0]}/{atlas}")

        video_info = ParseResult(
            video_url=video_url,
            cover_url=data["coverUrls"][0]["url"],
            title=data["caption"],
            author=data["userName"],
            pic_urls=images,
        )
        return video_info

    async def parse_url_by_api(self, url: str) -> ParseResult:
        """解析快手链接获取视频信息

        Args:
            url: 快手视频链接

        Returns:
            ParseResult: 快手视频信息
        """
        video_id = await self._extract_video_id(url)
        if not video_id:
            raise ParseException("无法从链接中提取视频ID")

        # 构造标准链接格式，用于API解析
        standard_url = f"https://www.kuaishou.com/short-video/{video_id}"
        # URL编码content参数避免查询字符串无效
        encoded_url = urllib.parse.quote(standard_url)
        api_url = self.api_url.format(encoded_url)

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=self.headers) as resp:
                if resp.status != 200:
                    raise ParseException(f"解析API返回错误状态码: {resp.status}")

                result = await resp.json()

            # 根据API返回示例，成功时code应为0
            if result.get("code") != 0 or not result.get("data"):
                raise ParseException(f"解析API返回错误: {result.get('msg', '未知错误')}")

            data = result["data"]
            video_url = data.get("url")
            if not video_url:
                raise ParseException("未获取到视频直链")

            return ParseResult(
                # 字段名称与回退值
                title=data.get("title", "未知标题"),
                cover_url=data.get("imageUrl", ""),
                video_url=video_url,
                # API可能不提供作者信息
                author=data.get("name", "无名"),
            )

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
