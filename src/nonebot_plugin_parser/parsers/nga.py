from html import unescape
import re
import time
from typing import ClassVar
from typing_extensions import override
from urllib.parse import urljoin

import httpx

from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..download import DOWNLOADER
from ..exception import ParseException
from .base import BaseParser
from .data import Author, ImageContent, ParseResult, Platform
from .utils import get_redirect_url


class NGAParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="nga", display_name="NGA")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("ngabbs.com", r"https?://ngabbs\.com/read\.php\?tid=\d+(?:[&#A-Za-z\d=_-]+)?"),
        ("nga.178.com", r"https?://nga\.178\.com/read\.php\?tid=\d+(?:[&#A-Za-z\d=_-]+)?"),
    ]

    @override
    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        url = matched.group(0)
        if "ngabbc.com" in url:
            # 处理 ngabbc.com 的跳转
            url = await get_redirect_url(url)

        headers = {**COMMON_HEADER}
        async with httpx.AsyncClient(headers=headers, timeout=COMMON_TIMEOUT) as client:
            try:
                resp = await client.get(url)
            except httpx.HTTPError as e:
                raise ParseException(f"请求失败: {e}")

        if resp.status_code != 200:
            raise ParseException(f"无法获取页面, HTTP {resp.status_code}")

        html = resp.text

        # 简单识别是否需要登录或被拦截
        if "需要" in html and ("登录" in html or "请登录" in html):
            raise ParseException("页面可能需要登录后访问")

        # 提取 title
        title = ""
        if m := re.search(r"<title>(.*?)</title>", html, re.I | re.S):
            title = unescape(m.group(1)).strip()
            # 常见分隔符清理
            for sep in [" - ", " | ", "—"]:
                if sep in title:
                    title = title.split(sep)[0].strip()
                    break

        # 尝试提取正文（多种常见容器）
        content_html = ""

        # 提取作者（尽量简单匹配）
        author = None
        # 常见作者位置：class="author"、楼主附近或 meta 标签
        if m := re.search(r"class=[\'\"]author[\'\"][^>]*>([^<\n]+)", html, re.I):
            author = m.group(1).strip()
        elif m := re.search(r"楼主[:：\s]*<[^>]*>([^<]+)<", html, re.I):
            author = m.group(1).strip()
        elif m := re.search(r"<meta\s+name=[\'\"]author[\'\"]\s+content=[\'\"]([^\'\"]+)[\'\"]", html, re.I):
            author = m.group(1).strip()

        # 提取时间（尝试多种常见格式）
        timestamp = None
        time_patterns = [
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})",
            r"(\d{4}年\d{1,2}月\d{1,2}日[\s\S]{0,30}?\d{1,2}:\d{2})",
        ]
        for tp in time_patterns:
            if m := re.search(tp, html):
                timestr = m.group(1)
                try:
                    if "年" in timestr:
                        # 例如 2025年10月3日 12:34
                        timestr_clean = re.sub(r"年|月", "-", timestr)
                        timestr_clean = re.sub(r"日", "", timestr_clean)
                        timestamp = time.mktime(time.strptime(timestr_clean.strip(), "%Y-%m-%d %H:%M"))
                    elif len(timestr) == 19:
                        timestamp = time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M:%S"))
                    else:
                        timestamp = time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M"))
                except Exception:
                    timestamp = None
                break

        # 提取图片链接
        raw_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
        pic_urls: list[str] = []
        for src in raw_imgs:
            src = src.strip()
            if not src or src.startswith("data:"):
                continue
            # 过滤常见图标/表情
            if any(x in src.lower() for x in ["favicon", "icon", "avatar", "smiley", "emot", "sml", "logo"]):
                continue
            # 处理 // 开头和 相对路径
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin("https://ngabbs.com", src)
            elif not src.startswith("http"):
                src = urljoin(url, src)

            # 仅保留常见图片/视频后缀
            if re.search(r"\.(?:jpg|jpeg|png|gif|webp|mp4|mp3)(?:\?.*)?$", src, re.I):
                if src not in pic_urls:
                    pic_urls.append(src)

        contents = []
        cover_path = None
        if pic_urls:
            pic_paths = await DOWNLOADER.download_imgs_without_raise(pic_urls, ext_headers=headers)
            contents.extend(ImageContent(p) for p in pic_paths)
            if pic_paths:
                cover_path = pic_paths[0]

        text = ""
        if content_html:
            # 去除标签并解码 HTML 实体
            text = re.sub(r"<[^>]+>", "", content_html)
            text = unescape(text).strip()

        return self.result(
            title=title,
            text=text,
            url=url,
            author=Author(name=author) if author else None,
            cover_path=cover_path,
            contents=contents,
            timestamp=timestamp,
        )
