"""百度贴吧帖页解析（访客 mo/q/m + PC SPA / Cookie）。"""

from __future__ import annotations

import codecs
import html as html_module
import re
from typing import Any, ClassVar
from urllib.parse import unquote

import curl_cffi
from bs4 import BeautifulSoup

from .base import BaseParser, PlatformEnum, handle, pconfig
from .data import ImageContent, MediaContent, Platform, VideoContent
from ..exception import ParseException

_OG_META_RE = re.compile(
    r'<meta (?:property|name)="(?P<key>og:[^"]+)" content="(?P<val>[^"]*)"',
    re.I,
)
_PIC_ITEM_RE = re.compile(
    r"https?://tiebapic\.baidu\.com/forum/pic/item/[^\"'\s<>]+",
    re.I,
)
_PIC_SRC_PARAM_RE = re.compile(
    r"src=(?:https?://|http%3A%2F%2F)(?:tiebapic\.baidu\.com%2Fforum%2Fpic%2Fitem%2F|tiebapic\.baidu\.com/forum/pic/item/)([^&\"'\s<>]+)",
    re.I,
)
_VIDEO_RE = re.compile(
    r"https?://tb-video\.bdstatic\.com/[^\"'\s<>]+\.mp4[^\"'\s<>]*",
    re.I,
)
_FORUM_KW_RE = re.compile(r"/f\?kw=([^&\"']+)", re.I)
_UNICODE_ESCAPE_RE = re.compile(r"\\u[0-9a-fA-F]{4}")


def _unescape(s: str) -> str:
    return html_module.unescape(s).replace("&amp;", "&")


def _decode_json_string(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if _UNICODE_ESCAPE_RE.search(text):
        try:
            text = codecs.decode(text, "unicode_escape")
        except Exception:
            pass
    return _unescape(text)


def _extract_og(html_text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for m in _OG_META_RE.finditer(html_text):
        k, v = m.group("key"), _unescape(m.group("val"))
        if k and v and k not in meta:
            meta[k] = v
    return meta


def _format_engagement(reply: str | None, share: str | None, like: str | None) -> str:
    parts: list[str] = []
    if reply is not None and reply != "":
        parts.append(f"{reply} 评论")
    if share is not None and share != "":
        parts.append(f"{share} 转发")
    if like is not None and like != "":
        parts.append(f"{like} 喜欢")
    return " · ".join(parts) if parts else ""


def _parse_stats_from_lines(lines: list[str]) -> tuple[str | None, str | None, str | None]:
    """标题区常见顺序：转发 / 评论数 / 喜欢数。"""
    share = reply = like = None
    try:
        if "转发" in lines:
            i = lines.index("转发")
            nums: list[str] = []
            for j in range(i + 1, min(i + 6, len(lines))):
                if re.fullmatch(r"\d+", lines[j]):
                    nums.append(lines[j])
                elif lines[j] in {"只看楼主", "全部回复", "热门"} or lines[j].startswith("全部回复"):
                    break
            if len(nums) >= 3:
                share, reply, like = nums[0], nums[1], nums[2]
            elif len(nums) == 2:
                reply, like = nums[0], nums[1]
            elif len(nums) == 1:
                reply = nums[0]
    except ValueError:
        pass
    m = re.search(r"全部回复\s*\((\d+)\)", "\n".join(lines))
    if m and reply is None:
        reply = m.group(1)
    return share, reply, like


def _parse_pc_action_bar(soup: BeautifulSoup) -> tuple[str | None, str | None, str | None]:
    """PC 首楼互动条：转发 / 评论 / 点赞 / 收藏。"""
    bar = soup.select_one(".action-bar-container") or soup.select_one(".action-bar")
    if not bar:
        return None, None, None
    share = reply = like = None
    for warp in bar.select(".item-warp"):
        icon = warp.select_one("use")
        href = (icon.get("xlink:href") or icon.get("href") or "") if icon else ""
        nums = [
            n.get_text(strip=True)
            for n in warp.select(".action-number")
            if n.get_text(strip=True)
        ]
        if "share_pb" in href:
            if nums and re.fullmatch(r"\d+", nums[0]):
                share = nums[0]
        elif "comment_pb" in href:
            reply = nums[0] if nums else reply
        elif "agree_pb" in href:
            like = nums[0] if nums else like
    return share, reply, like



def _parse_mo_like_from_thread(thread: dict[str, Any]) -> str | None:
    """访客 mo 帖级 JSON 无 agree_num；collect_status 为收藏态非点赞数。"""
    for key in ("agree_num", "zan_num", "like_num", "good_num", "praise_num"):
        if thread.get(key) is not None:
            return str(thread[key])
    return None


def _merge_engagement(
    reply: str | None, share: str | None, like: str | None
) -> str:
    return _format_engagement(reply, share, like)
def _extract_thread_fields(html_text: str, tid: str | None = None) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if tid:
        block = re.search(
            rf'"id":{re.escape(tid)},"reply_num":(\d+).*?"share_num":(\d+).*?"title":"((?:\\u[0-9a-fA-F]{{4}}|[^"])*)"',
            html_text,
            re.S,
        )
        if block:
            fields["reply_num"] = int(block.group(1))
            fields["share_num"] = int(block.group(2))
            fields["title"] = _decode_json_string(block.group(3))
        auth = re.search(
            rf'"id":{re.escape(tid)}.*?"author":\{{\s*"name"\s*:\s*"([^"]+)"',
            html_text,
            re.S,
        )
        if auth:
            fields["author"] = _decode_json_string(auth.group(1)) or auth.group(1)
    for key in ("reply_num", "share_num", "repost_num", "comment_num", "valid_post_num"):
        if key in fields:
            continue
        if m := re.search(rf'"{key}"\s*:\s*(\d+)', html_text):
            fields[key] = int(m.group(1))
    if "title" not in fields:
        if m := re.search(r'"title"\s*:\s*"((?:\\u[0-9a-fA-F]{{4}}|[^"])*)"', html_text):
            fields["title"] = _decode_json_string(m.group(1))
    if "author" not in fields:
        if m := re.search(r'"author"\s*:\s*\{{\s*"name"\s*:\s*"([^"]+)"', html_text):
            fields["author"] = m.group(1)
    if m := re.search(r'"forum_name"\s*:\s*"([^"]+)"', html_text):
        fields["forum_name"] = _decode_json_string(m.group(1))
    return fields


def _normalize_media_url(url: str) -> str:
    u = _unescape(url.strip())
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith("http"):
        u = "http://" + u
    return u.split("</div>")[0].split('"')[0]



def _resolve_query_src(url: str) -> str | None:
    """从 gss3 timg 等代理 URL 中取出内层 src。"""
    if "src=" not in url:
        return None
    q = url.split("?", 1)
    if len(q) < 2:
        return None
    from urllib.parse import parse_qs

    inner = parse_qs(q[1], keep_blank_values=True).get("src", [None])[0]
    if not inner:
        return None
    return _normalize_media_url(unquote(inner))


def _tieba_pic_to_imgsrc(url: str) -> str:
    """tiebapic 缩略/占位链转为 imgsrc 原图（实测体积更大）。"""
    m = re.search(r"/pic/item/([^?&]+)", url)
    if not m:
        return url
    name = m.group(1)
    if not name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        name = name + ".jpg"
    return f"http://imgsrc.baidu.com/forum/pic/item/{name}"


def _is_placeholder_image_url(url: str) -> bool:
    low = url.lower()
    if "tb2.bdstatic.com/tb/editor" in low:
        return True
    if "pic_icon" in low and "bdstatic.com" in low:
        return True
    if "/forum/w%3d" in low or "/forum/w=" in low:
        return True
    return False


def _extract_src_from_data_url(data_url: str) -> str | None:
    raw = _unescape(data_url)
    if "src=" in raw:
        part = raw.split("src=", 1)[1]
        inner = unquote(part.split("&", 1)[0])
        if "tiebapic.baidu.com" in inner or "imgsrc.baidu.com" in inner:
            return _tieba_pic_to_imgsrc(_normalize_media_url(inner))
    if "/pic/item/" in raw and not _is_placeholder_image_url(raw):
        return _tieba_pic_to_imgsrc(_normalize_media_url(raw.split("'")[0]))
    return None


def _extract_mo_first_floor_media(html_text: str, soup: BeautifulSoup) -> tuple[str | None, list[str]]:
    """仅从楼主首楼取头像与原图列表。"""
    floor = _mo_first_floor(soup)
    avatar_url: str | None = None
    pics: list[str] = []
    seen: set[str] = set()

    if not floor:
        return None, pics

    info = floor.get("data-info") or ""
    if info:
        info = html_module.unescape(info)
        if m := re.search(r'"portrait"\s*:\s*"([^"]+)"', info):
            portrait = m.group(1)
            p = portrait.strip()
            if p.startswith("http"):
                avatar_url = _normalize_media_url(p)
            else:
                avatar_url = _normalize_media_url(
                    f"http://tb.himg.baidu.com/sys/portrait/item/{p}"
                )
                if not re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", avatar_url, re.I):
                    avatar_url += ".jpg"

    if not avatar_url:
        for img in floor.select("img.user_img, img[class*='user']"):
            src = img.get("src") or ""
            if not src:
                continue
            src = _normalize_media_url(src)
            if inner := _resolve_query_src(src):
                avatar_url = inner
                break
            if "portrait" in src or "himg.baidu.com" in src:
                avatar_url = src
                break

    scope = floor.select_one("#pb_imgs") or floor.select_one('div.content[lz="1"]') or floor
    scope_html = str(scope)
    for m in re.finditer(r"data-url='([^']+)'", scope_html):
        if u := _extract_src_from_data_url(m.group(1)):
            key = re.search(r"/pic/item/([^?&]+)", u)
            key_s = key.group(1) if key else u
            if key_s in seen:
                continue
            seen.add(key_s)
            pics.append(u)

    if not pics:
        for m in _PIC_SRC_PARAM_RE.finditer(scope_html):
            tail = unquote(m.group(0).replace("src=", ""))
            if "tiebapic.baidu.com/forum/pic/item/" not in tail:
                continue
            u = _tieba_pic_to_imgsrc(_normalize_media_url(tail.split("&")[0]))
            key_m = re.search(r"/pic/item/([^?&]+)", u)
            key_s = key_m.group(1) if key_m else u
            if key_s in seen:
                continue
            seen.add(key_s)
            pics.append(u)

    return avatar_url, pics
def _extract_tiebapic_urls(html_text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def _pic_key(url: str) -> str:
        m = re.search(r"/pic/item/([^?]+)", url)
        return m.group(1) if m else url

    for m in _PIC_SRC_PARAM_RE.finditer(html_text):
        tail = unquote(m.group(0).replace("src=", ""))
        if "tiebapic.baidu.com/forum/pic/item/" not in tail:
            continue
        url = _normalize_media_url(tail.split("&")[0])
        key = _pic_key(url)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(url)
    for raw in _PIC_ITEM_RE.findall(html_text):
        url = _normalize_media_url(raw)
        if "/forum/pic/item/" not in url or "/w%3D" in url or "/w=" in url:
            continue
        key = _pic_key(url)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(url)
    return ordered


def _extract_video_urls(html_text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in _VIDEO_RE.findall(html_text):
        url = _normalize_media_url(raw)
        if "tb-video.bdstatic.com" not in url:
            continue
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def _pick_best_video(urls: list[str]) -> str | None:
    if not urls:
        return None
    for u in urls:
        if "smallvideo" in u:
            return _normalize_media_url(u)
    for u in urls:
        if "tieba-movideo" not in u:
            return _normalize_media_url(u)
    return _normalize_media_url(urls[0])


def _mo_first_floor(soup: BeautifulSoup) -> Any | None:
    for el in soup.select("li[tid]"):
        if el.select_one('div.content[lz="1"]') or el.select_one("div.content"):
            return el
    return soup.select_one("li[tid]")


def _clean_floor_body_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    for junk in (
        "下载贴吧APP",
        "打开贴吧App",
        "更多高清视频",
        "马上闯入高清视界",
        "打开手百APP阅读全文",
        "看高清大图",
    ):
        text = text.replace(junk, " ")
    text = re.sub(r"\d+\s*图", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_first_floor_body(floor: Any | None) -> str | None:
    if not floor:
        return None
    content_el = floor.select_one('div.content[lz="1"]') or floor.select_one("div.content")
    if not content_el:
        return None
    clone = BeautifulSoup(str(content_el), "html.parser")
    root = clone.select_one("div.content") or clone
    for tag in root.select("#pb_imgs, .pb_imgs, .pb_imgs_div, .img_desc, img, video, .videoFooter"):
        tag.decompose()
    return _clean_floor_body_text(root.get_text(" ", strip=True))


def _compose_card_text(body: str | None, engagement: str) -> str | None:
    body = _clean_floor_body_text(body)
    if body and engagement:
        return f"{body}\n{engagement}"
    if body:
        return body
    return engagement or None


class TiebaParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.TIEBA, display_name="百度贴吧")

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Referer": "https://tieba.baidu.com/",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        if ck := pconfig.tieba_ck:
            self.headers["cookie"] = ck

    @handle("tieba.baidu.com", r"tieba\.baidu\.com/p/(?P<tid>\d+)")
    async def _parse(self, searched: re.Match[str]):
        tid = searched.group("tid")
        url = f"https://tieba.baidu.com/p/{tid}/"
        html_text, source = await self._fetch_best_html(tid)
        if source == "mo":
            return await self._result_from_mo_html(html_text, url, tid)
        return await self._result_from_pc_html(html_text, url, tid)

    async def _guest_session_get(self, url: str, mobile: bool = False) -> str:
        headers = self.headers.copy()
        if mobile:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
            )
        async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
            await session.get("https://tieba.baidu.com/", headers=headers, timeout=30)
            r = await session.get(url, headers=headers, timeout=30)
            if r.status_code >= 400:
                raise ParseException(f"贴吧页面请求失败: HTTP {r.status_code}")
            return r.text

    async def _fetch_best_html(self, tid: str) -> tuple[str, str]:
        mo_url = f"https://tieba.baidu.com/mo/q/m?kz={tid}"
        try:
            mo_html = await self._guest_session_get(mo_url, mobile=True)
            if len(mo_html) > 30_000 and ("threadInfo" in mo_html or "'thread'" in mo_html):
                return mo_html, "mo"
        except Exception:
            pass

        pc_url = f"https://tieba.baidu.com/p/{tid}/"
        headers = self.headers.copy()
        async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
            if not pconfig.tieba_ck:
                await session.get("https://tieba.baidu.com/", headers=headers, timeout=30)
            r = await session.get(pc_url, headers=headers, timeout=30)
            if r.status_code >= 400:
                raise ParseException(f"贴吧页面请求失败: HTTP {r.status_code}")
            text = r.text
        if len(text) < 50_000 and "pb-title" not in text:
            raise ParseException(
                "贴吧正文需登录 Cookie 或 mo 页不可用：可配置 PARSER_TIEBA_CK"
            )
        return text, "pc"

    async def _result_from_mo_html(self, html_text: str, url: str, tid: str):
        soup = BeautifulSoup(html_text, "html.parser")
        thread = _extract_thread_fields(html_text, tid)
        floor = _mo_first_floor(soup)

        title = thread.get("title")
        if not title:
            og = _extract_og(html_text)
            raw = og.get("og:title", "")
            title = unquote(raw).split("-")[0].strip() if raw else None
        if not title:
            raise ParseException("贴吧未解析到标题")

        author_name = thread.get("author")
        avatar_url, pic_urls_floor = _extract_mo_first_floor_media(html_text, soup)
        if floor and not author_name:
            for a in floor.select("a.user_name, a[class*='user_name']"):
                t = a.get_text(strip=True).rstrip(":")
                if t and len(t) < 64:
                    author_name = t
                    break

        share = str(thread["share_num"]) if thread.get("share_num") is not None else None
        reply = str(thread["reply_num"]) if thread.get("reply_num") is not None else None
        like = _parse_mo_like_from_thread(thread)
        if floor:
            btn = floor.select_one(".btn_reply .btn_icon")
            if btn and btn.get_text(strip=True).isdigit() and reply is None:
                reply = btn.get_text(strip=True)

        engagement = _format_engagement(reply, share, like)

        text_body = _extract_first_floor_body(floor)
        card_text = _compose_card_text(text_body, engagement)

        pic_urls = pic_urls_floor or _extract_tiebapic_urls(html_text)
        pic_urls = [_tieba_pic_to_imgsrc(pu) for pu in pic_urls]
        video_urls = _extract_video_urls(html_text)

        contents: list[MediaContent] = []
        if video_urls:
            vurl = _pick_best_video(video_urls)
            cover = pic_urls[0] if pic_urls else None
            if cover:
                cover = _tieba_pic_to_imgsrc(cover)
            contents.append(self.create_video(vurl, cover, duration=None))
        else:
            for pu in pic_urls[:12]:
                if _is_placeholder_image_url(pu):
                    continue
                contents.append(self.create_image(_tieba_pic_to_imgsrc(pu)))

        if not contents:
            raise ParseException("贴吧未解析到媒体")

        forum = thread.get("forum_name")
        if not forum and floor:
            el = floor.select_one(".post_title_text")
            if el:
                forum = el.get_text(strip=True)

        result = self.result(
            title=title,
            text=card_text,
            author=self.create_author(author_name or "unknown", avatar_url),
            url=url,
            contents=contents,
            extra={
                "info": None,
                "tieba_reply": reply,
                "tieba_share": share,
                "tieba_like": like,
                "forum_kw": forum,
                "thread_id": tid,
                "body": text_body,
                "source": "mo",
            },
        )
        if len(contents) == 1 and isinstance(contents[0], VideoContent):
            result.extra.setdefault("content_type", "视频")
        elif len(contents) > 1:
            result.extra.setdefault("content_type", "图集")
        return result

    async def _result_from_pc_html(self, html_text: str, url: str, tid: str):
        soup = BeautifulSoup(html_text, "html.parser")
        title_el = soup.select_one(".pb-title")
        title = title_el.get_text(" ", strip=True) if title_el else None
        if title:
            title = re.sub(r"^视频\s+", "", title).strip()
        if not title:
            og = _extract_og(html_text)
            title = og.get("og:title", "").split("-")[0].strip() or None
        if not title:
            thread = _extract_thread_fields(html_text, tid)
            title = thread.get("title")
        if not title:
            raise ParseException("贴吧未解析到标题")

        center = soup.select_one(".image-text") or soup.select_one(".center-content") or soup.body
        if not center:
            raise ParseException("贴吧页面结构异常")

        lines = [ln.strip() for ln in center.get_text("\n", strip=True).split("\n") if ln.strip()]
        share, reply, like = _parse_stats_from_lines(lines)
        bar_share, bar_reply, bar_like = _parse_pc_action_bar(soup)
        share = share or bar_share
        reply = reply or bar_reply
        like = like or bar_like

        thread = _extract_thread_fields(html_text, tid)
        if like is None:
            like = _parse_mo_like_from_thread(thread)
        if like is None:
            like = "0"
        if reply is None and thread.get("reply_num") is not None:
            reply = str(thread["reply_num"])
        if share is None and thread.get("share_num") is not None:
            share = str(thread["share_num"])

        author_name = thread.get("author")
        avatar_url = None
        for a in center.select('a[href*="/home/main"]'):
            t = a.get_text("\n", strip=True).split("\n")[0].strip()
            if t and t not in {"我的", "关注"} and len(t) < 64:
                author_name = author_name or t
                break
        if img := center.select_one("img.avatar-img"):
            avatar_url = img.get("src")

        engagement = _format_engagement(reply, share, like)

        text_body = None
        if center:
            for sel in (".d_post_content", ".p_content", ".d_post_content_main"):
                el = center.select_one(sel)
                if el:
                    text_body = _clean_floor_body_text(el.get_text(" ", strip=True))
                    if text_body:
                        break
        card_text = _compose_card_text(text_body, engagement)

        pic_urls = [_tieba_pic_to_imgsrc(pu) for pu in _extract_tiebapic_urls(html_text)]
        video_urls = _extract_video_urls(html_text)

        contents: list[MediaContent] = []
        if video_urls:
            vurl = _pick_best_video(video_urls)
            cover = pic_urls[0] if pic_urls else None
            contents.append(self.create_video(vurl, cover, duration=None))
        else:
            for pu in pic_urls[:12]:
                if _is_placeholder_image_url(pu):
                    continue
                contents.append(self.create_image(pu))

        if not contents:
            raise ParseException("贴吧未解析到媒体")

        forum = None
        if m := _FORUM_KW_RE.search(html_text):
            forum = unquote(m.group(1))

        result = self.result(
            title=title,
            text=card_text,
            author=self.create_author(author_name or "unknown", avatar_url),
            url=url,
            contents=contents,
            extra={
                "info": None,
                "tieba_reply": reply,
                "tieba_share": share,
                "tieba_like": like,
                "forum_kw": forum,
                "thread_id": tid,
                "body": text_body,
                "source": "pc",
            },
        )
        if len(contents) == 1 and isinstance(contents[0], VideoContent):
            result.extra.setdefault("content_type", "视频")
        elif len(contents) > 1:
            result.extra.setdefault("content_type", "图集")
        return result

    async def _result_from_html(self, html_text: str, url: str, tid: str):
        """兼容 Relay 导出 HTML 测试入口。"""
        if "pb-title" in html_text and len(html_text) > 200_000:
            return await self._result_from_pc_html(html_text, url, tid)
        return await self._result_from_mo_html(html_text, url, tid)
