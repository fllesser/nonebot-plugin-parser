"""Instagram 帖子 / Reels 解析（yt-dlp）。"""

from __future__ import annotations

import asyncio
import html
import json
import re
from typing import Any, ClassVar
from urllib.parse import parse_qs, unquote, urlparse

import yt_dlp
import curl_cffi
from httpx import AsyncClient
from msgspec import convert

from .base import BaseParser, PlatformEnum, handle, pconfig
from .cookie import save_cookies_with_netscape
from .data import Author, MediaContent, Platform, VideoContent
from ..download import yt_dlp_downloader
from ..download.ytdlp import VideoInfo
from ..exception import ParseException

_INSTAGRAM_MEDIA_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?instagram\.com/(?:[^/]+/)?"
    r"(?P<kind>p|reel|reels|tv)/(?P<shortcode>[A-Za-z0-9_-]+)",
    re.I,
)
_INSTAGRAM_SHARE_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?instagram\.com/share/"
    r"(?P<kind>p|reel)/(?P<shortcode>[A-Za-z0-9_-]+)",
    re.I,
)
_INSTAGRAM_SHORT_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagr\.am/(?P<kind>p|reel|tv)/(?P<shortcode>[A-Za-z0-9_-]+)",
    re.I,
)
_IG_ME_RE = re.compile(
    r"(?:https?://)?ig\.me/(?P<kind>reel)/(?P<shortcode>[A-Za-z0-9_-]+)",
    re.I,
)
_L_INSTAGRAM_RE = re.compile(
    r"(?:https?://)?l\.instagram\.com/\?(?P<query>[^\s]+)",
    re.I,
)
_PROFILE_PIC_JSON_RE = re.compile(
    r"\"profile_pic_url(?:_hd)?\"\\s*:\\s*\"(?P<url>(?:\\\\.|[^\"\\\\])+?)\"",
    re.I,
)
_PROFILE_PIC_IMG_RE = re.compile(
    r"https://[^\"'\s>]+cdninstagram\.com/[^\"'\s>]*profile[^\"'\s>]*",
    re.I,
)


_OG_META_RE = re.compile(
    r'<meta (?:property|name)="(?P<key>og:[^"]+|twitter:[^"]+)" content="(?P<val>[^"]*)"',
    re.I,
)
_POST_FEED_IMAGE_RE = re.compile(
    r"https://[^\"'\s>]+cdninstagram\.com/v/t51\.(?:82787|2885)-15/[^\"'\s>]+",
    re.I,
)


def _html_unescape_meta(text: str) -> str:
    return html.unescape(text).replace("&amp;", "&")


def _extract_og_meta(html_text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for match in _OG_META_RE.finditer(html_text):
        key = _html_unescape_meta(match.group("key"))
        val = _html_unescape_meta(match.group("val"))
        if key and val and key not in meta:
            meta[key] = val
    return meta


def _dedupe_carousel_image_urls(html_text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in _POST_FEED_IMAGE_RE.findall(html_text):
        url = _html_unescape_meta(raw)
        if url in seen:
            continue
        seen.add(url)
        ordered.append(url)
    return ordered


def _parse_instagram_og_caption(title: str | None) -> str | None:
    if not title:
        return None
    m = re.search(r'on Instagram:\s*"(.+?)"\s*$', title, re.I | re.S)
    if m:
        return _html_unescape_meta(m.group(1)).strip()
    m = re.search(r'Instagram:\s*"(.+?)"', title, re.I | re.S)
    if m:
        return _html_unescape_meta(m.group(1)).strip()
    return _html_unescape_meta(title).strip() or None


def _parse_instagram_og_engagement(description: str | None) -> str | None:
    if not description:
        return None
    desc = _html_unescape_meta(description)
    m = re.match(
        r"^([\d.,]+[KkMm]?)\s+likes?,\s*([\d,]+)\s+comments?",
        desc,
        re.I,
    )
    if m:
        likes, comments = m.group(1), m.group(2)
        return f"{likes} likes · {comments} comments"
    return None


def _split_instagram_og_title_text(
    og_title: str | None, og_description: str | None
) -> tuple[str | None, str | None]:
    caption = _parse_instagram_og_caption(og_title)
    engagement = _parse_instagram_og_engagement(og_description)
    if engagement:
        return caption, engagement
    if og_description:
        desc = _html_unescape_meta(og_description)
        if caption and caption in desc:
            return caption, None
        return caption, desc.strip() or None
    return caption, None


def _extract_instagram_username_from_page(
    html_text: str,
    meta: dict[str, str],
    page_url: str,
) -> str:
    for source in (
        meta.get("og:url"),
        page_url,
    ):
        if not source:
            continue
        m = re.search(
            r"instagram\.com/([A-Za-z0-9_.]+)/(?:p|reel|reels|tv)/",
            source,
            re.I,
        )
        if m:
            return m.group(1)

    og_desc = meta.get("og:description") or ""
    desc = _html_unescape_meta(og_desc)
    m = re.match(
        r"^[\d.,]+[KkMm]?\s+likes?,\s*[\d,]+\s+comments?\s*-\s*([A-Za-z0-9_.]+)\s+on\b",
        desc,
        re.I,
    )
    if m:
        return m.group(1)

    for source in (meta.get("og:title"), meta.get("twitter:title")):
        if not source:
            continue
        s = _html_unescape_meta(source)
        if m := re.search(r"@([A-Za-z0-9_.]+)", s):
            return m.group(1)

    for m in re.finditer(r'"username":"([A-Za-z0-9_.]+)"', html_text):
        name = m.group(1)
        if name not in {"instagram", "meta", "media"}:
            return name

    return ""


def _is_instagram_no_video_ytdlp_error(exc: BaseException) -> bool:
    return "there is no video in this post" in str(exc).lower()


def _normalize_instagram_kind(kind: str | None) -> str | None:
    if not kind:
        return None
    lowered = kind.lower()
    if lowered == "reels":
        return "reel"
    if lowered in {"p", "reel", "tv"}:
        return lowered
    return None


def _canonical_instagram_url(kind: str | None, shortcode: str | None) -> str | None:
    normalized = _normalize_instagram_kind(kind)
    if not normalized or not shortcode:
        return None
    return f"https://www.instagram.com/{normalized}/{shortcode}/"


def _unescape_json_url(url: str) -> str:
    try:
        return json.loads(f'"{url}"')
    except json.JSONDecodeError:
        return url.replace("\\/", "/").replace("\\u0026", "&")


def _extract_profile_pic_from_html(html: str) -> str | None:
    for match in _PROFILE_PIC_JSON_RE.finditer(html):
        url = _unescape_json_url(match.group("url"))
        if url.startswith("http"):
            return url
    for match in _PROFILE_PIC_IMG_RE.finditer(html):
        return match.group(0)
    return None


def _extract_instagram_target(url: str) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None

    for pattern in (_INSTAGRAM_MEDIA_RE, _INSTAGRAM_SHARE_RE, _INSTAGRAM_SHORT_RE, _IG_ME_RE):
        if match := pattern.search(raw):
            return _canonical_instagram_url(match.group("kind"), match.group("shortcode"))

    if match := _L_INSTAGRAM_RE.search(raw):
        query = match.group("query") or ""
        encoded = parse_qs(query, keep_blank_values=True).get("u", [None])[0]
        if encoded:
            target = unquote(encoded)
            return _extract_instagram_target(target)
    return None


def _coerce_ytdlp_entry(info_dict: dict) -> dict:
    data = dict(info_dict)
    duration = data.get("duration")
    if isinstance(duration, float):
        data["duration"] = int(duration)
    elif data.get("duration") is None:
        data["duration"] = 0

    timestamp = data.get("timestamp")
    if isinstance(timestamp, float):
        data["timestamp"] = int(timestamp)
    elif data.get("timestamp") is None:
        data["timestamp"] = 0

    channel = (data.get("channel") or data.get("uploader") or "").strip()
    uploader = (data.get("uploader") or channel or "unknown").strip()
    data["channel"] = channel
    data["uploader"] = uploader
    data["channel_id"] = str(data.get("channel_id") or data.get("uploader_id") or uploader)
    data["title"] = (data.get("title") or "").strip()
    data["thumbnail"] = data.get("thumbnail") or ""
    data["description"] = (data.get("description") or "").strip()
    return data


def _instagram_page_url(searched: re.Match[str]) -> str:
    raw = searched.string.strip()
    fragment = searched.group(0).split("?")[0]
    if fragment.lower().startswith("http"):
        return fragment
    if raw.lower().startswith("http"):
        return raw.split()[0].split("?")[0]
    return f"https://{fragment}"


class InstagramParser(BaseParser):
    platform: ClassVar[Platform] = Platform(
        name=PlatformEnum.INSTAGRAM, display_name="Instagram"
    )

    def __init__(self):
        super().__init__()
        self.cookies_file = pconfig.config_dir / "instagram_cookies.txt"
        if pconfig.instagram_ck:
            save_cookies_with_netscape(
                pconfig.instagram_ck,
                self.cookies_file,
                "instagram.com",
            )

    @handle(
        "instagram.com",
        r"(?:https?://)?(?:www\.|m\.)?instagram\.com/(?:[^/]+/)?(?:share/)?(?:p|reel|reels|tv)/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?",
    )
    @handle(
        "instagr.am",
        r"(?:https?://)?(?:www\.)?instagr\.am/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?",
    )
    @handle(
        "ig.me",
        r"(?:https?://)?ig\.me/reel/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?",
    )
    @handle(
        "l.instagram.com",
        r"(?:https?://)?l\.instagram\.com/\?[^\s]+",
    )
    async def _parse(self, searched: re.Match[str]) -> Any:
        if yt_dlp_downloader is None:
            raise ParseException("未安装 yt-dlp，无法解析 Instagram")

        page_url = _instagram_page_url(searched)
        url = _extract_instagram_target(page_url) or await self._resolve_instagram_url(page_url)
        if not url:
            raise ParseException(f"无法识别 Instagram 链接: {searched.string.strip()}")

        return await self._result_from_ytdlp(url)

    def _cookie_path(self):
        return self.cookies_file if self.cookies_file.is_file() else None

    async def _resolve_instagram_url(self, url: str) -> str:
        final_url = await self.get_final_url(url, headers=self.headers)
        if canonical := _extract_instagram_target(final_url):
            return canonical

        parsed = urlparse(final_url)
        if parsed.netloc.lower().endswith("instagram.com"):
            path = parsed.path.rstrip("/")
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 2:
                kind = _normalize_instagram_kind(parts[-2])
                shortcode = parts[-1]
                if kind and shortcode:
                    return _canonical_instagram_url(kind, shortcode)

        raise ParseException(f"无法识别 Instagram 链接: {url}")

    @staticmethod
    def _coerce_ytdlp_info(info_dict: dict) -> dict:
        data = dict(info_dict)
        entries = data.get("entries")
        if isinstance(entries, list):
            normalized_entries = []
            for entry in entries:
                if not isinstance(entry, dict):
                    normalized_entries.append(entry)
                    continue
                normalized_entries.append(_coerce_ytdlp_entry(entry))
            data["entries"] = normalized_entries
        return _coerce_ytdlp_entry(data)

    async def _fetch_author_avatar_from_api(self, username: str) -> str | None:
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = self.headers.copy()
        headers.update(
            {
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"https://www.instagram.com/{username}/",
            }
        )
        if pconfig.instagram_ck:
            headers["cookie"] = pconfig.instagram_ck
        try:
            async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
                response = await session.get(url, headers=headers, timeout=20)
                if response.status_code != 200:
                    return None
                user = ((response.json().get("data") or {}).get("user") or {})
                avatar = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
                return avatar if isinstance(avatar, str) and avatar.startswith("http") else None
        except Exception:
            return None

    async def _fetch_author_avatar_url(self, username: str | None, page_url: str) -> str | None:
        clean = (username or "").strip().lstrip("@")
        if clean:
            if avatar := await self._fetch_author_avatar_from_api(clean):
                return avatar

        targets = []
        if clean:
            targets.append(f"https://www.instagram.com/{clean}/")
        targets.append(page_url)

        headers = self.headers.copy()
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        if pconfig.instagram_ck:
            headers["cookie"] = pconfig.instagram_ck

        async with AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True, verify=False) as client:
            for target in targets:
                try:
                    response = await client.get(target)
                    if response.status_code >= 400:
                        continue
                    if avatar := _extract_profile_pic_from_html(response.text):
                        return avatar
                except Exception:
                    continue
        return None

    async def _build_author(self, channel: str, uploader: str, page_url: str) -> Author:
        display = f"@{channel}" if channel and not uploader.startswith("@") else uploader
        avatar_url = await self._fetch_author_avatar_url(channel or uploader, page_url)
        return self.create_author(display, avatar_url)

    async def _result_from_ytdlp(self, url: str):
        ydl_opts = yt_dlp_downloader._extract_base_opts.copy()
        if path := self._cookie_path():
            ydl_opts["cookiefile"] = str(path)

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info_dict = await asyncio.to_thread(_extract)
        except Exception as exc:
            if _is_instagram_no_video_ytdlp_error(exc):
                return await self._result_from_photo_html(url)
            raise
        if not info_dict:
            raise ParseException("Instagram 媒体信息获取失败")

        info_dict = self._coerce_ytdlp_info(info_dict)

        if info_dict.get("_type") == "playlist":
            entries = [e for e in info_dict.get("entries") or [] if e]
            if entries:
                info_dict = dict(info_dict)
                info_dict["entries"] = entries
                return await self._result_from_playlist(info_dict, url)
            return await self._result_from_photo_html(url)

        video_info = convert(info_dict, VideoInfo)
        return await self._result_from_single(video_info, url)


    async def _fetch_post_html(self, page_url: str) -> str:
        headers = self.headers.copy()
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        if pconfig.instagram_ck:
            headers["cookie"] = pconfig.instagram_ck
        async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
            response = await session.get(page_url, headers=headers, timeout=30)
            if response.status_code >= 400:
                raise ParseException(f"Instagram 页面请求失败: {response.status_code}")
            return response.text

    async def _result_from_photo_html(self, page_url: str):
        html_text = await self._fetch_post_html(page_url)
        meta = _extract_og_meta(html_text)
        image_urls = _dedupe_carousel_image_urls(html_text)
        if not image_urls and meta.get("og:image"):
            image_urls = [meta["og:image"]]
        if not image_urls:
            raise ParseException("Instagram 图片帖未解析到媒体")

        og_title = meta.get("og:title") or meta.get("twitter:title")
        og_desc = meta.get("og:description")
        title, text = _split_instagram_og_title_text(og_title, og_desc)
        channel = _extract_instagram_username_from_page(html_text, meta, page_url)
        uploader = channel or "unknown"

        contents: list[MediaContent] = [self.create_image(u) for u in image_urls]
        result = self.result(
            title=title,
            text=text,
            author=await self._build_author(channel, uploader, page_url),
            timestamp=None,
            url=page_url,
            contents=contents,
            extra={"content_type": "图集"} if len(contents) > 1 else {},
        )
        return result

    async def _result_from_single(self, video_info: VideoInfo, page_url: str):
        channel = (video_info.channel or "").strip()
        uploader = (video_info.uploader or channel or "unknown").strip()

        title = (video_info.title or "").strip() or None
        text = (video_info.description or "").strip() or None
        duration = int(video_info.duration or 0)

        contents: list[MediaContent] = []
        cookiefile = self._cookie_path()

        if duration and duration <= pconfig.duration_maximum:
            contents.append(
                self.create_video(
                    yt_dlp_downloader.download_video(page_url, cookiefile),
                    video_info.thumbnail,
                    duration=float(duration),
                )
            )
        elif video_info.thumbnail:
            contents.append(self.create_image(video_info.thumbnail))

        if not contents:
            raise ParseException("Instagram 未解析到可发送的媒体")

        result = self.result(
            title=title,
            text=text,
            author=await self._build_author(channel, uploader, page_url),
            timestamp=video_info.timestamp or None,
            url=page_url,
            contents=contents,
        )
        if len(contents) == 1 and isinstance(contents[0], VideoContent):
            result.extra.setdefault("content_type", "视频")
        return result

    async def _result_from_playlist(self, info_dict: dict, page_url: str):
        entries = [e for e in info_dict.get("entries") or [] if e]
        if not entries:
            raise ParseException("Instagram 图集为空")

        channel = info_dict.get("channel") or entries[0].get("channel")
        uploader = info_dict.get("uploader") or entries[0].get("uploader") or "unknown"

        contents: list[MediaContent] = []
        cookiefile = self._cookie_path()

        for entry in entries:
            thumb = entry.get("thumbnail")
            entry_url = entry.get("webpage_url") or entry.get("url")
            entry_duration = int(entry.get("duration") or 0)
            has_video = entry.get("vcodec") not in (None, "none") or entry_duration > 0

            if has_video and entry_url and entry_duration <= pconfig.duration_maximum:
                contents.append(
                    self.create_video(
                        yt_dlp_downloader.download_video(entry_url, cookiefile),
                        thumb,
                        duration=float(entry_duration),
                    )
                )
            elif thumb:
                contents.append(self.create_image(thumb))
            elif entry_url:
                contents.append(self.create_image(entry_url))

        if not contents:
            raise ParseException("Instagram 图集媒体不可用")

        return self.result(
            title=info_dict.get("title"),
            text=(info_dict.get("description") or "").strip() or None,
            author=await self._build_author(str(channel or ""), str(uploader), page_url),
            timestamp=info_dict.get("timestamp"),
            url=page_url,
            contents=contents,
            extra={"content_type": "图集"} if len(contents) > 1 else {},
        )
