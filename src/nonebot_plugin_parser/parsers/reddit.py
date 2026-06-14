from __future__ import annotations

import html
import json
import re
from typing import Any, ClassVar
from urllib.parse import urlparse

import curl_cffi
from httpx import AsyncClient

from .base import BaseParser, PlatformEnum, handle
from .data import MediaContent, Platform, ParseResult, VideoContent
from .task import PathTask
from ..config import pconfig
from ..exception import ParseException

_COMMENTS_JSON = re.compile(
    r"(?:https?://)?(?:www\.|old\.)?reddit\.com/r/[^/]+/comments/(?P<post_id>[a-z0-9]+)",
    re.I,
)


def _unescape_url(url: str) -> str:
    return html.unescape(url).replace("&amp;", "&")




_SUBMIT_CROSSPOST_RE = re.compile(
    r"\[\]\(https?://(?:www\.)?reddit\.com/submit/[^)]+\)",
    re.I,
)


def _clean_reddit_selftext(text: str | None) -> str | None:
    """去掉正文里的 crosspost / submit 占位链接等 UI 残留"""
    if not text:
        return None
    t = text.strip()
    t = _SUBMIT_CROSSPOST_RE.sub("", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t or None


def _redgifs_slug_from_url(url: str) -> str | None:
    m = re.search(r"redgifs\.com/watch/([a-zA-Z0-9_-]+)", url, re.I)
    return m.group(1) if m else None


def _redgifs_mp4_url_from_post(post: dict[str, Any]) -> str | None:
    """RedGIFs CDN：从 oembed 缩略图或 watch URL 推导 mp4 地址"""
    post_url = _unescape_url(post.get("url") or "")
    domain = (post.get("domain") or "").lower()
    if "redgifs.com" not in post_url and domain != "redgifs.com":
        return None
    secure = post.get("secure_media") or post.get("media") or {}
    thumb = (secure.get("oembed") or {}).get("thumbnail_url") or ""
    m = re.search(
        r"media\.redgifs\.com/([A-Za-z0-9_-]+?)(?:-poster)?\.(?:jpg|png)",
        thumb,
        re.I,
    )
    if m:
        return f"https://media.redgifs.com/{m.group(1)}.mp4"
    slug = _redgifs_slug_from_url(post_url)
    if not slug:
        return None
    return f"https://media.redgifs.com/{slug[0].upper() + slug[1:]}.mp4"

def _post_id_from_match(searched: re.Match[str]) -> str:
    if pid := searched.groupdict().get("post_id"):
        return pid
    if m := _COMMENTS_JSON.search(searched.group(0)):
        return m.group("post_id")
    raise ParseException("无法识别 Reddit 帖子 ID")
_REDDIT_SHARE_IN_TEXT = re.compile(
    r"(?:https?://)?(?:www\.|old\.)?reddit\.com/r/[^/]+/s/(?P<share_id>[A-Za-z0-9]+)",
    re.I,
)



def _reddit_author_avatar_url_from_about(data: dict[str, Any]) -> str | None:
    """user/about.json：优先 snoovatar，其次 icon_img"""
    for key in ("snoovatar_img", "icon_img"):
        raw = _unescape_url(str(data.get(key) or ""))
        if raw.startswith("http") and "avatar_default" not in raw:
            return raw
    for key in ("snoovatar_img", "icon_img"):
        raw = _unescape_url(str(data.get(key) or ""))
        if raw.startswith("http"):
            return raw
    return None


def _reddit_author_avatar_from_post(post: dict[str, Any]) -> str | None:
    raw = _unescape_url(str(post.get("author_icon_img") or ""))
    return raw if raw.startswith("http") else None

def _reddit_share_page_url(searched: re.Match[str]) -> str:
    """从匹配结果还原完整 /r/.../s/... 分享页 URL（移动端简略链接）"""
    raw = searched.string
    if m := _REDDIT_SHARE_IN_TEXT.search(raw):
        path = m.group(0)
        if path.lower().startswith("http"):
            return path.split("?")[0]
        return f"https://{path.split('?')[0]}"
    fragment = searched.group(0).split("?")[0]
    if fragment.lower().startswith("http"):
        return fragment
    return f"https://{fragment}"


async def _fetch_redgifs_media_urls(slug: str) -> tuple[str | None, str | None]:
    """RedGIFs API：temporary token + v2/gifs/{id}"""
    if not slug:
        return None, None
    gid = slug.lower()
    try:
        async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
            token = await _redgifs_bearer_token()
            if not token:
                return None, None
            headers = {
                "Authorization": f"Bearer {token}",
                "Referer": "https://www.redgifs.com/",
                "Origin": "https://www.redgifs.com",
            }
            resp = await session.get(
                f"https://api.redgifs.com/v2/gifs/{gid}",
                headers=headers,
                timeout=20,
            )
            if resp.status_code != 200:
                return None, None
            urls = (resp.json().get("gif") or {}).get("urls") or {}
            mp4 = _unescape_url(
                urls.get("hd") or urls.get("sd") or urls.get("silent") or ""
            )
            cover = _unescape_url(urls.get("poster") or urls.get("thumbnail") or "")
            return (
                mp4 if mp4.startswith("http") else None,
                cover if cover.startswith("http") else None,
            )
    except Exception:
        return None, None



def _reddit_post_page_url(post: dict[str, Any]) -> str:
    permalink = post.get("permalink") or ""
    if permalink.startswith("/"):
        return f"https://www.reddit.com{permalink}"
    if permalink.startswith("http"):
        return permalink
    post_id = post.get("id") or ""
    subreddit = post.get("subreddit") or ""
    if subreddit and post_id:
        return f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/"
    return "https://www.reddit.com/"


def _reddit_post_removed_message(post: dict[str, Any]) -> str | None:
    cat = post.get("removed_by_category")
    if cat:
        return f"该帖已被 Reddit 移除（{cat}），无可用媒体。"
    if post.get("removed_by") or post.get("banned_by"):
        return "该帖已被移除，无可用媒体。"
    return None


def _reddit_video_download_headers(
    post: dict[str, Any], base_headers: dict[str, str]
) -> dict[str, str]:
    headers = dict(base_headers)
    page = _reddit_post_page_url(post)
    headers.setdefault("Referer", page)
    headers.setdefault("Origin", "https://www.reddit.com")
    return headers


class RedditParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.REDDIT, display_name="Reddit")

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.reddit.com/",
            }
        )
        if pconfig.reddit_ck:
            self.headers["cookie"] = pconfig.reddit_ck

    @handle("reddit.com", r"(?:www\.|old\.)?reddit\.com/r/[^/]+/comments/(?P<post_id>[a-z0-9]+)")
    @handle("redd.it", r"redd\.it/(?P<post_id>[a-z0-9]+)")
    @handle(
        "reddit.com",
        r"(?:www\.|old\.)?reddit\.com/r/[^/]+/s/(?P<share_id>[A-Za-z0-9]+)",
    )
    async def _parse(self, searched: re.Match[str]) -> ParseResult:
        raw = searched.string
        if "/s/" in raw and "/comments/" not in raw:
            url = _reddit_share_page_url(searched)
            canonical = await self._resolve_share_url(url)
            if "/comments/" not in canonical:
                raise ParseException(f"无法解析 Reddit 分享链接: {raw}")
            keyword, searched = self.search_url(canonical)
            return await self.parse(keyword, searched)
        post_id = _post_id_from_match(searched)
        if "redd.it" in searched.group(0) and "comments" not in searched.group(0):
            canonical = await self.get_final_url(f"https://redd.it/{post_id}")
            keyword, searched = self.search_url(canonical)
            return await self.parse(keyword, searched)

        post = await self._fetch_post_data(post_id)
        return await self._build_result(post)
    async def _resolve_share_url(self, url: str) -> str:
        """分享链接 /s/... 跟随重定向到带 post_id 的 comments 页"""
        try:
            async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
                response = await session.get(
                    url,
                    headers=self.headers,
                    timeout=30,
                    allow_redirects=True,
                )
                if response.status_code < 400:
                    return str(response.url)
        except Exception:
            pass
        return await self.get_final_url(url, headers=self.headers)

    async def _fetch_post_data(self, post_id: str) -> dict[str, Any]:
        url = f"https://www.reddit.com/comments/{post_id}.json"
        params = {"raw_json": "1"}
        last_error: Exception | None = None

        try:
            async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
                response = await session.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30,
                    allow_redirects=True,
                )
                if response.status_code == 200:
                    return self._extract_post_from_listing(response.json())
        except Exception as exc:
            last_error = exc

        async with AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
            verify=False,
        ) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                if response.status_code == 403 and not pconfig.reddit_ck:
                    raise ParseException(
                        "Reddit 需要配置 parser_reddit_ck（建议含 token_v2 与 reddit_session）"
                    )
                raise ParseException(
                    f"Reddit 帖子获取失败 HTTP {response.status_code}"
                ) from last_error
            return self._extract_post_from_listing(response.json())

    @staticmethod
    def _extract_post_from_listing(payload: list[Any]) -> dict[str, Any]:
        try:
            return payload[0]["data"]["children"][0]["data"]
        except (IndexError, KeyError, TypeError) as exc:
            raise ParseException("Reddit JSON 结构异常") from exc

    async def _build_result(self, post: dict[str, Any]) -> ParseResult:
        title = post.get("title")
        author_name = post.get("author") or "unknown"
        created = post.get("created_utc")
        timestamp = int(created) if created is not None else None
        text = _clean_reddit_selftext((post.get("selftext") or "").strip() or None)
        permalink = post.get("permalink") or ""
        page_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink

        avatar_url = _reddit_author_avatar_from_post(post)
        if not avatar_url and author_name and author_name.lower() not in ("[deleted]", "automoderator"):
            avatar_url = await self._fetch_reddit_user_avatar_url(author_name)
        author = self.create_author(author_name, avatar_url)

        contents = await self._collect_media(post)
        if not contents:
            preview = post.get("thumbnail")
            if preview and str(preview).startswith("http"):
                contents.append(self.create_image(_unescape_url(str(preview))))

        prefixed = post.get("subreddit_name_prefixed") or (
            f"r/{post['subreddit']}" if post.get("subreddit") else None
        )
        extra: dict[str, Any] = {}
        if prefixed:
            extra["subreddit_prefixed"] = prefixed
            if icon_url := await self._fetch_subreddit_community_icon(post.get("subreddit")):
                extra["subreddit_icon"] = PathTask(
                    self.downloader.download_img(icon_url, ext_headers=self.headers)
                )

        if notice := _reddit_post_removed_message(post):
            extra["info"] = notice
            extra["post_removed"] = True
        elif post.get("is_gallery") and not contents:
            extra["info"] = "图集元数据不可用（可能已移除或未登录可见）。"

        result = self.result(
            title=title,
            text=text,
            author=author,
            timestamp=timestamp,
            url=page_url,
            contents=contents,
            extra=extra,
        )

        if len(contents) == 1 and isinstance(contents[0], VideoContent):
            result.extra.setdefault("content_type", "视频")
        elif len(result.img_contents) > 1:
            result.extra.setdefault("content_type", "图集")

        return result


    async def _fetch_reddit_user_avatar_url(self, username: str) -> str | None:
        if not username or username.lower() in ("[deleted]", "automoderator"):
            return None
        url = f"https://www.reddit.com/user/{username}/about.json"
        params = {"raw_json": "1"}
        try:
            async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
                response = await session.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=20,
                )
                if response.status_code != 200:
                    return None
                data = response.json().get("data") or {}
                return _reddit_author_avatar_url_from_about(data)
        except Exception:
            return None

    async def _fetch_subreddit_community_icon(self, subreddit: str | None) -> str | None:
        if not subreddit:
            return None
        url = f"https://www.reddit.com/r/{subreddit}/about.json"
        params = {"raw_json": "1"}
        try:
            async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
                response = await session.get(
                    url, params=params, headers=self.headers, timeout=20
                )
                if response.status_code != 200:
                    return None
                data = response.json().get("data") or {}
        except Exception:
            return None
        icon = _unescape_url(data.get("community_icon") or data.get("icon_img") or "")
        return icon if icon.startswith("http") else None

    async def _collect_media(self, post: dict[str, Any]) -> list[MediaContent]:
        contents: list[MediaContent] = []

        if post.get("is_gallery"):
            contents.extend(self._media_from_gallery(post))
            if contents:
                return contents

        if post.get("is_video"):
            video = self._media_from_reddit_video(post)
            if video:
                contents.append(video)
                return contents

        post_url = _unescape_url(post.get("url") or "")
        domain = (post.get("domain") or "").lower()

        if domain in {"i.redd.it", "i.imgur.com"} or _is_direct_image(post_url):
            contents.append(self.create_image(post_url))
            return contents

        if post_url and ("v.redd.it" in post_url or post.get("is_video")):
            video = self._media_from_reddit_video(post, fallback_link=post_url)
            if video:
                contents.append(video)
                return contents

        oembed_list = await self._media_from_oembed_or_external(post)
        if oembed_list:
            contents.extend(oembed_list)
            return contents

        if "external-preview.redd.it" in post_url and "format=mp4" in post_url:
            contents.append(
                self.create_video(
                    post_url,
                    _pick_thumbnail(post),
                    is_gif=bool(post.get("is_gif")),
                    download_headers=_reddit_video_download_headers(post, self.headers),
                )
            )
            return contents

        return contents

    async def _redgifs_download_headers(self) -> dict[str, str]:
        """RedGIFs CDN 不能用 Reddit Referer/Cookie，否则会 403。"""
        headers: dict[str, str] = {
            "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.redgifs.com/",
            "Origin": "https://www.redgifs.com",
        }
        if token := await _redgifs_bearer_token():
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _media_from_oembed_or_external(self, post: dict[str, Any]) -> list[MediaContent]:
        """RedGIFs 等外链视频（rich:video + oembed）"""
        domain = (post.get("domain") or "").lower()
        post_url = _unescape_url(post.get("url") or "")
        if "redgifs.com" not in domain and "redgifs.com" not in post_url:
            return []

        slug = _redgifs_slug_from_url(post_url)
        mp4, api_cover = await _fetch_redgifs_media_urls(slug or "")
        if not mp4:
            mp4 = _redgifs_mp4_url_from_post(post)

        secure = post.get("secure_media") or post.get("media") or {}
        oembed = secure.get("oembed") or {}
        reddit_preview = _pick_thumbnail(post)
        cover = (
            reddit_preview
            or api_cover
            or _unescape_url(oembed.get("thumbnail_url") or "")
        )

        rg_headers = await self._redgifs_download_headers()
        if mp4:
            return [
                self.create_video(
                    mp4,
                    cover,
                    is_gif=False,
                    download_headers=rg_headers,
                )
            ]
        if cover:
            return [self.create_image(cover)]
        return []


    def _media_from_gallery(self, post: dict[str, Any]) -> list[MediaContent]:
        items = (post.get("gallery_data") or {}).get("items") or []
        metadata = post.get("media_metadata") or {}
        out: list[MediaContent] = []

        for item in items:
            media_id = item.get("media_id")
            if not media_id:
                continue
            meta = metadata.get(media_id)
            if not meta:
                continue
            kind = meta.get("e")
            source = meta.get("s") or {}

            if kind == "Image":
                url = _unescape_url(source.get("u") or "")
                if url:
                    out.append(self.create_image(url))
            elif kind == "AnimatedImage":
                gif_url = _unescape_url(
                    source.get("gif") or source.get("mp4") or source.get("u") or ""
                )
                preview = _gallery_item_preview(source)
                if gif_url:
                    out.append(self.create_gif(gif_url, cover_url=preview))
            elif kind == "RedditVideo":
                video_url = _unescape_url(
                    source.get("dashUrl") or source.get("hlsUrl") or source.get("u") or ""
                )
                if video_url:
                    out.append(
                        self.create_video(
                            video_url,
                            _gallery_item_preview(source),
                            duration=source.get("duration"),
                            download_headers=_reddit_video_download_headers(post, self.headers),
                        )
                    )
        return out

    def _media_from_reddit_video(
        self,
        post: dict[str, Any],
        *,
        fallback_link: str | None = None,
    ) -> MediaContent | None:
        media = post.get("secure_media") or post.get("media") or {}
        reddit_video = media.get("reddit_video") or {}
        duration = reddit_video.get("duration")

        video_url = _unescape_url(
            reddit_video.get("fallback_url")
            or reddit_video.get("scrubber_media_url")
            or reddit_video.get("hls_url")
            or reddit_video.get("dash_url")
            or ""
        )

        if not video_url and fallback_link:
            packaged = _packaged_mp4_from_html_embed(post)
            if packaged:
                video_url, duration = packaged

        if not video_url:
            return None

        cover = _pick_thumbnail(post, reddit_video)
        is_gif = bool(post.get("is_gif")) or (
            fallback_link is not None and "gif" in (fallback_link or "").lower()
        )

        return self.create_video(
            video_url,
            cover,
            duration=duration,
            is_gif=is_gif,
            download_headers=_reddit_video_download_headers(post, self.headers),
        )


def _pick_thumbnail(post: dict[str, Any], reddit_video: dict[str, Any] | None = None) -> str | None:
    for candidate in (
        (reddit_video or {}).get("thumbnail"),
        post.get("thumbnail"),
        post.get("preview", {}).get("images", [{}])[0].get("source", {}).get("url"),
    ):
        if candidate and str(candidate).startswith("http"):
            return _unescape_url(str(candidate))
    return None


def _gallery_item_preview(source: dict[str, Any]) -> str | None:
    for key in ("u", "gif", "mp4"):
        val = source.get(key)
        if val and str(val).startswith("http"):
            return _unescape_url(str(val))
    return None


def _is_direct_image(url: str) -> bool:
    if not url:
        return False
    path = urlparse(url).path.lower()
    return path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))


def _packaged_mp4_from_html_embed(post: dict[str, Any]) -> tuple[str, float | None] | None:
    for key in ("media_embed", "secure_media_embed"):
        blob = post.get(key)
        if not blob:
            continue
        raw = json.dumps(blob) if isinstance(blob, dict) else str(blob)
        if "packaged-media.redd.it" not in raw and "playbackMp4s" not in raw:
            continue
        try:
            if isinstance(blob, dict) and "content" in blob:
                inner = json.loads(blob["content"]) if isinstance(blob["content"], str) else blob
            else:
                inner = blob
            permutations = (
                inner.get("playbackMp4s", {}).get("permutations")
                or inner.get("playback_mp4s", {}).get("permutations")
                or []
            )
            if not permutations:
                continue
            best = permutations[-1].get("source") or permutations[-1]
            url = _unescape_url(best.get("url") or "")
            duration = inner.get("playbackMp4s", {}).get("duration")
            if url:
                return url, float(duration) if duration else None
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
    return None


_REDGIFS_TOKEN: str | None = None


async def _redgifs_bearer_token() -> str | None:
    global _REDGIFS_TOKEN
    if _REDGIFS_TOKEN:
        return _REDGIFS_TOKEN
    try:
        async with curl_cffi.AsyncSession(impersonate="chrome131") as session:
            auth = await session.get(
                "https://api.redgifs.com/v2/auth/temporary", timeout=20
            )
            if auth.status_code != 200:
                return None
            _REDGIFS_TOKEN = auth.json().get("token") or auth.json().get(
                "access_token"
            )
            return _REDGIFS_TOKEN
    except Exception:
        return None
