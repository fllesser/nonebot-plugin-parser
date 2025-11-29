import re
import json
import time
import random
import asyncio
from typing import ClassVar

from bs4 import Tag, BeautifulSoup
from httpx import HTTPError, AsyncClient

from .base import Platform, BaseParser, PlatformEnum, handle
from ..exception import ParseException


class NGAParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.NGA, display_name="NGA")

    def __init__(self):
        super().__init__()
        extra_headers = {
            "Referer": "https://nga.178.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.headers.update(extra_headers)
        self.base_img_url = "https://img.nga.178.com/attachments"

    @staticmethod
    def nga_url(tid: str | int) -> str:
        return f"https://nga.178.com/read.php?tid={tid}"

    # ("ngabbs.com", r"https?://ngabbs\.com/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    # ("nga.178.com", r"https?://nga\.178\.com/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    # ("bbs.nga.cn", r"https?://bbs\.nga\.cn/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    @handle("ngabbs.com", r"tid=(?P<tid>\d+)")
    @handle("nga.178.com", r"tid=(?P<tid>\d+)")
    @handle("bbs.nga.cn", r"tid=(?P<tid>\d+)")
    async def _parse(self, searched: re.Match[str]):
        # 从匹配对象中获取原始URL
        tid = searched.group("tid")
        url = self.nga_url(tid)

        async with AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
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

            except HTTPError as e:
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
        title = None
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
        author = self.create_author(author) if author else None
        # 提取时间 - 从第一个帖子的 postdate0
        timestamp = None
        time_tag = soup.find(id="postdate0")
        if time_tag and isinstance(time_tag, Tag):
            timestr = time_tag.get_text(strip=True)
            timestamp = int(time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M")))

        # 提取文本 - postcontent0
        text = None
        content_tag = soup.find(id="postcontent0")
        contents = []
        if content_tag and isinstance(content_tag, Tag):
            text = content_tag.get_text("\n", strip=True)
            # 清理 BBCode 标签并限制长度
            img_urls: list[str] = re.findall(r"\[img\](.*?)\[/img\]", text)
            img_urls = [self.base_img_url + url[1:] for url in img_urls]
            contents.extend(self.create_image_contents(img_urls))
            text = self.clean_nga_text(text)

        return self.result(
            title=title,
            text=text,
            url=url,
            author=author,
            contents=contents,
            timestamp=timestamp,
        )

    @staticmethod
    def clean_nga_text(text: str, max_length: int = 500) -> str:
        rules: list[tuple[str, str, int]] = [
            # 移除图片标签（完整和不完整的）
            (r"\[img\][^\[\]]*\[/img\]", "", 0),
            (r"\[img\][^\[\]]*", "", 0),
            # 处理URL标签，保留链接文本
            (r"\[url=[^\]]*\]([^\[]*?)\[/url\]", r"\1", 0),
            (r"\[url\]([^\[]*?)\[/url\]", r"\1", 0),
            # 移除引用标签
            (r"\[quote\].*?\[/quote\]", "", re.DOTALL),
            # 处理格式标签，保留文本内容（b, i, u）
            (r"\[(b|i|u)\](.*?)\[/\1\]", r"\2", re.DOTALL),
            # 处理带属性的格式标签（color, size）
            (r"\[(color|size)=[^\]]*\](.*?)\[/\1\]", r"\2", re.DOTALL),
            # 移除其他未配对的标签
            (r"\[[^]]+\]", "", 0),
            # 清理空白字符
            (r"\n{3,}", "\n\n", 0),  # 多个换行符压缩为两个
            (r"[ \t]+", " ", 0),  # 多个空格/制表符压缩为一个空格
            (r"\n\s+\n", "\n\n", 0),  # 清理空行中的空白字符
        ]

        for rule in rules:
            pattern, replacement, flags = rule[0], rule[1], rule[2]
            text = re.sub(pattern, replacement, text, flags=flags)

        text = text.strip()

        # 限制文本长度
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text
