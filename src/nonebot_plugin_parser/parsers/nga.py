import asyncio
import json
import random
import re
import time
from typing import ClassVar
from typing_extensions import override

from bs4 import BeautifulSoup, Tag
import httpx

from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..exception import ParseException
from .base import BaseParser
from .data import Author, ParseResult, Platform


class NGAParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="nga", display_name="NGA")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("ngabbs.com", r"https?://ngabbs\.com/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
        ("nga.178.com", r"https?://nga\.178\.com/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
        ("bbs.nga.cn", r"https?://bbs\.nga\.cn/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    ]

    @override
    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源,包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        tid = matched.group("tid")
        url = f"https://nga.178.com/read.php?tid={tid}"

        # NGA 需要更完整的请求头来避免403
        headers = {
            **COMMON_HEADER,
            "Referer": "https://nga.178.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        async with httpx.AsyncClient(headers=headers, timeout=COMMON_TIMEOUT, follow_redirects=True) as client:
            try:
                # 第一次请求可能返回403，但包含设置cookie的JavaScript
                resp = await client.get(url)

                # 如果返回403且包含guestJs cookie设置，提取cookie并重试
                if resp.status_code == 403 and "guestJs" in resp.text:
                    # 从JavaScript中提取guestJs cookie值
                    cookie_match = re.search(
                        r"document\.cookie\s*=\s*['\"]guestJs=([^;'\"]+)",
                        resp.text,
                    )
                    if cookie_match:
                        guest_js = cookie_match.group(1)
                        # 设置cookie并重试
                        client.cookies.set("guestJs", guest_js, domain=".178.com")
                        # 等待一小段时间（模拟JavaScript的setTimeout）
                        await asyncio.sleep(0.3)

                        # 添加随机参数避免缓存（模拟JavaScript的行为）
                        rand_param = random.randint(0, 999)
                        separator = "&" if "?" in url else "?"
                        retry_url = f"{url}{separator}rand={rand_param}"

                        resp = await client.get(retry_url)

            except httpx.HTTPError as e:
                raise ParseException(f"请求失败: {e}")

        if resp.status_code != 200:
            raise ParseException(f"无法获取页面, HTTP {resp.status_code}")

        html = resp.text

        # 简单识别是否需要登录或被拦截
        if "需要" in html and ("登录" in html or "请登录" in html):
            raise ParseException("页面可能需要登录后访问")

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html, "html.parser")

        # 提取 title - 从 postsubject0
        title = ""
        title_tag = soup.find(id="postsubject0")
        if title_tag and isinstance(title_tag, Tag):
            title = title_tag.get_text(strip=True)

        # 提取作者 - 先从 postauthor0 标签提取 uid，再从 JavaScript 中查找用户名
        author = None
        author_tag = soup.find(id="postauthor0")
        if author_tag and isinstance(author_tag, Tag):
            # 从 href 属性中提取 uid: href="nuke.php?func=ucp&uid=24278093"
            href = author_tag.get("href", "")
            uid_match = re.search(r"[?&]uid=(\d+)", str(href))
            if uid_match:
                uid = uid_match.group(1)
                # 从 JavaScript 的 commonui.userInfo.setAll() 中查找对应用户名
                script_pattern = r"commonui\.userInfo\.setAll\s*\(\s*(\{.*?\})\s*\)"
                script_match = re.search(script_pattern, html, re.DOTALL)
                if script_match:
                    try:
                        user_info_json = script_match.group(1)
                        user_info = json.loads(user_info_json)
                        # 使用提取的 uid 查找用户名
                        if uid in user_info:
                            author = user_info[uid].get("username")
                    except (json.JSONDecodeError, KeyError):
                        # JSON 解析失败或数据结构不符合预期,保持 author 为 None
                        pass

        # 提取时间 - 从第一个帖子的 postdate0
        timestamp = None
        time_tag = soup.find(id="postdate0")
        if time_tag and isinstance(time_tag, Tag):
            timestr = time_tag.get_text(strip=True)
            timestamp = time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M"))

        return self.result(
            title=title,
            url=url,
            author=Author(name=author) if author else None,
            timestamp=timestamp,
        )
