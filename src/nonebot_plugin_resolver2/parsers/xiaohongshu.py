import json
import re
from urllib.parse import parse_qs, urlparse

import httpx
from nonebot import logger

from ..config import rconfig
from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..exception import ParseException
from .data import ImageContent, ParseResult, VideoContent
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

    async def parse_url(self, url: str) -> ParseResult:
        """解析小红书 URL

        Args:
            url (str): 小红书 URL

        Returns:
            ParseResult: 解析结果

        Raises:
            ParseException: 小红书分享链接不完整
            ParseException: 小红书 cookie 可能已失效
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

        # 构造完整 URL
        url = f"https://www.xiaohongshu.com/explore/{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}"
        async with httpx.AsyncClient(headers=self.headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.get(url)
            html = response.text

        pattern = r"window.__INITIAL_STATE__=(.*?)</script>"
        matched = re.search(pattern, html)
        if not matched:
            raise ParseException("小红书分享链接失效或内容已删除")

        json_str = matched.group(1)
        json_str = json_str.replace("undefined", "null")
        json_obj = json.loads(json_str)
        try:
            note_data = json_obj["note"]["noteDetailMap"][xhs_id]["note"]
            resource_type, note_title, note_desc = note_data["type"], note_data["title"], note_data["desc"]
        except KeyError as e:
            logger.error(f"小红书解析失败: {e}")
            raise ParseException("小红书 cookie 可能已失效")

        title_desc = f"{note_title}\n{note_desc}"
        img_urls = []
        video_url = ""
        if resource_type == "normal":
            image_list = note_data["imageList"]
            img_urls = [item["urlDefault"] for item in image_list]
        elif resource_type == "video":
            stream = note_data["video"]["media"]["stream"]
            for code in ("h264", "h265", "av1"):
                if item := stream.get(code):
                    video_url = item[0]["masterUrl"]
                    break
            if not video_url:
                raise ParseException("小红书视频解析失败")
        else:
            raise ParseException(f"不支持的小红书链接类型: {resource_type}")

        return ParseResult(
            title=title_desc,
            cover_url="",
            content=VideoContent(video_url=video_url) if video_url else ImageContent(pic_urls=img_urls),
            author=note_data["user"]["nickname"],
        )
