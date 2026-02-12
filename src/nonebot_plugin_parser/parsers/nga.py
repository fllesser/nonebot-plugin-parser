import re
import json
import time
import random
import asyncio
from typing import ClassVar

from bs4 import Tag, BeautifulSoup
from httpx import HTTPError, AsyncClient
from nonebot import logger

from .base import Platform, BaseParser, PlatformEnum, handle
from ..exception import ParseException


class NGAParser(BaseParser):
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
    def build_url_by_tid(tid: str | int) -> str:
        return f"https://nga.178.com/read.php?tid={tid}"

    # ("ngabbs.com", r"https?://ngabbs\.com/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    # ("nga.178.com", r"https?://nga\.178\.com/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    # ("bbs.nga.cn", r"https?://bbs\.nga\.cn/read\.php\?tid=(?P<tid>\d+)(?:[&#A-Za-z\d=_-]+)?"),
    @handle("nga", r"tid=(?P<tid>\d+)")
    async def _parse(self, searched: re.Match[str]):
        # 从匹配对象中获取原始URL
        tid = int(searched.group("tid"))
        url = self.build_url_by_tid(tid)

        async with AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
            try:
                # 第一次请求可能返回 403，但包含设置 cookie 的 JavaScript
                resp = await client.get(url)
                # 如果返回 403 且包含 guestJs cookie设置，提取cookie并重试
                if resp.status_code == 403 and "guestJs" in resp.text:
                    logger.debug("第一次请求 403 错误, 包含 guestJs cookie, 重试请求")
                    # 从JavaScript中提取 guestJs cookie 值
                    if matched := re.search(r"document\.cookie\s*=\s*['\"]guestJs=([^;'\"]+)", resp.text):
                        guest_js = matched.group(1)
                        client.cookies.set("guestJs", guest_js, domain=".178.com")
                        # 等待一小段时间（模拟 JavaScript 的 setTimeout）
                        await asyncio.sleep(0.3)
                        # 添加随机参数避免缓存（模拟 JavaScript 的行为）
                        rand_param = random.randint(0, 999)
                        separator = "&" if "?" in url else "?"
                        retry_url = f"{url}{separator}rand={rand_param}"

                        # 重试请求
                        resp = await client.get(retry_url)

            except HTTPError as e:
                raise ParseException(f"请求失败: {e}")

        if resp.status_code != 200:
            raise ParseException(f"无法获取页面, HTTP {resp.status_code}")

        html = resp.text

        # 简单识别是否需要登录或被拦截
        if "需要" in html and ("登录" in html or "请登录" in html):
            raise ParseException("页面可能需要登录后访问")

        soup = BeautifulSoup(html, "html.parser")

        # 提取 title - 从 postsubject0 标签提取
        title = None
        title_tag = soup.find(id="postsubject0")
        if title_tag and isinstance(title_tag, Tag):
            title = title_tag.get_text(strip=True)

        # 提取作者信息 - 先从 postauthor0 标签提取 uid，再从 JavaScript 中查找用户名
        author = None
        author_tag = soup.find(id="postauthor0")
        if author_tag and isinstance(author_tag, Tag):
            # 从 href 属性中提取 uid: href="nuke.php?func=ucp&uid=24278093"
            href = author_tag.get("href", "")
            if matched := re.search(r"[?&]uid=(\d+)", str(href)):
                uid = str(matched.group(1))
                # 从 JavaScript 的 commonui.userInfo.setAll() 中查找对应用户名
                script_pattern = r"commonui\.userInfo\.setAll\s*\(\s*(\{.*?\})\s*\)"
                if matched := re.search(script_pattern, html, re.DOTALL):
                    user_info = matched.group(1)
                    try:
                        user_info = json.loads(user_info)
                        if uid in user_info:
                            author = user_info[uid].get("username")
                    except (json.JSONDecodeError, KeyError):
                        pass

        author = self.create_author(author) if author else None

        # 提取时间 - 从第一个帖子的 postdate0
        timestamp = None
        time_tag = soup.find(id="postdate0")
        if time_tag and isinstance(time_tag, Tag):
            timestr = time_tag.get_text(strip=True)
            timestamp = int(time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M")))

        # 提取文本 - postcontent0
        text, contents = None, []
        content_tag = soup.find(id="postcontent0")
        if content_tag and isinstance(content_tag, Tag):
            text = content_tag.get_text("\n", strip=True)
            lines = text.split("\n")
            temp_text = ""
            for line in lines:
                if line.startswith("[img]"):
                    # [img]./mon_202602/10/-lmuf1Q1aw-hzwpZ2dT3cSl4-bs.webp[/img]
                    img_url = self.base_img_url + line[6:-6]
                    contents.append(self.create_graphics_content(img_url, text=temp_text))
                    temp_text = ""
                # 去除其他标签, 仅保留文本
                elif "[" in line:
                    if clean_line := re.sub(r"\[[^\]]*?\]", "", line).strip():
                        temp_text += clean_line + "\n"
                else:
                    temp_text += line + "\n"
            text = temp_text.strip()

        return self.result(
            title=title,
            url=url,
            author=author,
            text=text,
            contents=contents,
            timestamp=timestamp,
        )
