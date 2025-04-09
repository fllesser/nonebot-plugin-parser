import json
import re
from urllib.parse import parse_qs, urlparse

import aiohttp

from ..config import rconfig
from ..constant import COMMON_HEADER
from ..exception import ParseException
from .data import ImageContent, ShareUrlInfo, VideoAuthor, VideoContent
from .utils import get_redirect_url


class XiaoHongShuParser:
    def __init__(self):
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.9",
            **COMMON_HEADER,
        }
        if rconfig.r_xhs_ck:
            self.headers["cookie"] = rconfig.r_xhs_ck

    async def parse_url(self, url: str) -> ShareUrlInfo:
        """解析小红书 URL

        Args:
            url (str): 小红书 URL

        Raises:
            Exception: 没有符合的小红书 URL
            Exception: 小红书 cookies 可能已失效

        Returns:
            tuple[str, list[str], str]: 标题, 图片列表, 视频 URL
        """
        # 处理 xhslink 短链
        if "xhslink" in url:
            url = await get_redirect_url(url, self.headers)
        # ?: 非捕获组
        pattern = r"(?:/explore/|/discovery/item/|source=note&noteId=)(\w+)"
        matched = re.search(pattern, url)
        if not matched:
            raise ParseException("小红书分享链接不完整")
        xhs_id = matched.group(1)
        # 解析 URL 参数
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        # 提取 xsec_source 和 xsec_token
        xsec_source = params.get("xsec_source", [None])[0] or "pc_feed"
        xsec_token = params.get("xsec_token", [None])[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.xiaohongshu.com/explore/{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}",
                headers=self.headers,
            ) as resp:
                html = await resp.text()

        pattern = r"window.__INITIAL_STATE__=(.*?)</script>"
        matched = re.search(pattern, html)
        if not matched:
            raise ParseException("小红书 cookie 可能已失效")

        json_str = matched.group(1)
        json_str = json_str.replace("undefined", "null")
        json_obj = json.loads(json_str)
        try:
            note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
        except KeyError:
            raise ParseException("小红书 cookie 可能已失效")
        # 资源类型 normal 图，video 视频
        resource_type = note_data["type"]
        # 标题
        note_title = note_data["title"]
        # 描述
        note_desc = note_data["desc"]
        title_desc = f"{note_title}\n{note_desc}"
        if resource_type == "normal":
            image_list = note_data["imageList"]
            img_urls = [item["urlDefault"] for item in image_list]
            content = ImageContent(urls=img_urls)
        elif resource_type == "video":
            video_url = note_data["video"]["media"]["stream"]["h264"][0]["masterUrl"]
            content = VideoContent(url=video_url)
        else:
            raise ParseException(f"不支持的小红书链接类型: {resource_type}")
        return ShareUrlInfo(
            title=title_desc,
            content=content,
            author=VideoAuthor(name=note_data["user"]["nickname"]),
        )
