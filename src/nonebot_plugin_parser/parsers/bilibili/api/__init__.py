"""Bilibili API 客户端 — 基于 curl_cffi"""

from __future__ import annotations

import time
import uuid
import hashlib
import urllib.parse
from functools import reduce

from msgspec import json as msgspec_json
from nonebot import logger
from curl_cffi.requests import AsyncSession

from .models import NavData, ApiResponse, PlayUrlData
from ....exception import ParseException

# WBI 签名用索引表 (来自 bilibili-api-python)
_OE = [
    46,
    47,
    18,
    2,
    53,
    8,
    23,
    32,
    15,
    50,
    10,
    31,
    58,
    3,
    45,
    35,
    27,
    43,
    5,
    49,
    33,
    9,
    42,
    19,
    29,
    28,
    14,
    39,
    12,
    38,
    41,
    13,
    37,
    48,
    7,
    16,
    24,
    55,
    40,
    61,
    26,
    17,
    0,
    1,
    60,
    51,
    30,
    4,
    22,
    25,
    54,
]

BILI_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
}


def _split_wbi_key(url: str) -> str:
    """从 wbi_img url 中提取文件名（不含扩展名）"""
    return url.split("/")[-1].split(".")[0]


def _enc_wbi(params: dict, mixin_key: str) -> dict:
    """WBI 签名"""
    params.pop("w_rid", None)
    params["wts"] = int(time.time())
    params.setdefault("web_location", 1550101)
    sorted_query = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((sorted_query + mixin_key).encode()).hexdigest()
    return params


class BiliCredential:
    """B站登录凭证 (替代 bilibili_api.Credential)"""

    def __init__(
        self,
        sessdata: str | None = None,
        bili_jct: str | None = None,
        buvid3: str | None = None,
        buvid4: str | None = None,
        dedeuserid: str | None = None,
        ac_time_value: str | None = None,
    ):
        self.sessdata = sessdata
        self.bili_jct = bili_jct
        self.buvid3 = buvid3
        self.buvid4 = buvid4
        self.dedeuserid = dedeuserid
        self.ac_time_value = ac_time_value

    def get_cookies(self) -> dict[str, str]:
        cookies = {
            "SESSDATA": self.sessdata or "",
            "buvid3": self.buvid3 or "",
            "buvid4": self.buvid4 or "",
            "bili_jct": self.bili_jct or "",
            "ac_time_value": self.ac_time_value or "",
        }
        if self.dedeuserid:
            cookies["DedeUserID"] = self.dedeuserid
        return cookies

    @staticmethod
    def from_cookies(cookies: dict[str, str]) -> BiliCredential:
        return BiliCredential(
            sessdata=cookies.get("SESSDATA"),
            bili_jct=cookies.get("bili_jct"),
            buvid3=cookies.get("buvid3"),
            buvid4=cookies.get("buvid4"),
            dedeuserid=cookies.get("DedeUserID"),
            ac_time_value=cookies.get("ac_time_value"),
        )

    def has_sessdata(self) -> bool:
        return bool(self.sessdata)

    def has_bili_jct(self) -> bool:
        return bool(self.bili_jct)

    def has_ac_time_value(self) -> bool:
        return bool(self.ac_time_value)


class BiliAPIClient:
    """B站 API 客户端，封装 curl_cffi session 和 WBI 签名"""

    def __init__(self, credential: BiliCredential | None = None):
        self._credential = credential
        self._session: AsyncSession | None = None
        self._wbi_mixin_key: str = ""
        self._headers = BILI_HEADERS.copy()

    _IMPERSONATE = "chrome131"

    @staticmethod
    def _default_cookies() -> dict[str, str]:
        return {
            "buvid3": f"{uuid.uuid4().hex[:16]}infoc",
            "buvid4": str(uuid.uuid4()),
        }

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            cookies = self._credential.get_cookies() if self._credential else {}
            # 即使没有 credential 也需要基础 cookie
            defaults = self._default_cookies()
            for k, v in defaults.items():
                cookies.setdefault(k, v)
            self._session = AsyncSession(
                impersonate=self._IMPERSONATE,
                headers=self._headers,
                cookies=cookies,
            )
        # 每次请求前更新 cookie (credential 可能已刷新)
        if self._credential:
            self._session.cookies.update(self._credential.get_cookies())
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        data: dict | None = None,
        wbi: bool = False,
        raise_on_error: bool = True,
    ) -> ApiResponse:
        """通用请求方法"""
        session = await self._get_session()

        if wbi:
            params = params or {}
            mixin_key = await self._get_wbi_mixin_key()
            params = _enc_wbi(params, mixin_key)

        for attempt in range(2):
            try:
                resp = await session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    impersonate=self._IMPERSONATE,
                )
                resp.raise_for_status()
            except Exception as e:
                if attempt == 0 and wbi:
                    # WBI key 可能过期，刷新重试
                    self._wbi_mixin_key = ""
                    continue
                raise ParseException(f"B站 API 请求失败: {e}") from e

            # 检查响应是否为 JSON (B站 WAF 会返回 HTML)
            content_type = resp.headers.get("content-type", "")
            if "application/json" not in content_type and "text/json" not in content_type:
                if raise_on_error:
                    raise ParseException(
                        f"B站 API 请求被风控 (HTTP {resp.status_code}), 响应类型: {content_type or '未知'}"
                    )
                return ApiResponse(code=-1, message="风控响应")

            api_resp: ApiResponse = msgspec_json.decode(resp.content, type=ApiResponse)
            if api_resp.code != 0 and raise_on_error:
                raise ParseException(f"B站 API 错误 (code={api_resp.code}): {api_resp.message}")
            return api_resp

        raise ParseException("B站 API 请求失败 (重试后仍失败)")

    async def _get(
        self, url: str, *, params: dict | None = None, wbi: bool = False, raise_on_error: bool = True
    ) -> ApiResponse:
        return await self._request("GET", url, params=params, wbi=wbi, raise_on_error=raise_on_error)

    async def _post(self, url: str, *, data: dict | None = None, wbi: bool = False) -> ApiResponse:
        return await self._request("POST", url, data=data, wbi=wbi)

    # ── WBI 签名 ──

    async def _get_wbi_mixin_key(self) -> str:
        if self._wbi_mixin_key:
            return self._wbi_mixin_key

        nav = await self._get("https://api.bilibili.com/x/web-interface/nav", raise_on_error=False)
        nav_data = msgspec_json.decode(msgspec_json.encode(nav.data), type=NavData) if nav.data else NavData()

        if not nav_data.wbi_img:
            raise ParseException("无法获取 WBI 签名密钥")

        wbi = nav_data.wbi_img
        ae = _split_wbi_key(wbi.img_url) + _split_wbi_key(wbi.sub_url)
        le = reduce(lambda s, i: s + (ae[i] if i < len(ae) else ""), _OE, "")
        self._wbi_mixin_key = le[:32]
        return self._wbi_mixin_key

    # ── 凭证管理 ──

    async def check_valid(self) -> bool:
        """检查凭证是否有效"""
        try:
            nav = await self._get("https://api.bilibili.com/x/web-interface/nav")
            nav_data = msgspec_json.decode(msgspec_json.encode(nav.data), type=NavData) if nav.data else NavData()
            return nav_data.isLogin
        except ParseException:
            return False

    async def check_refresh(self) -> bool:
        """检查是否需要刷新 cookies"""
        try:
            resp = await self._get("https://passport.bilibili.com/x/passport-login/web/cookie/info")
            return bool(resp.data.get("refresh", False)) if resp.data else False
        except ParseException:
            return False

    async def refresh_credential(self) -> bool:
        """刷新登录凭证"""
        if not self._credential or not self._credential.has_bili_jct() or not self._credential.has_ac_time_value():
            logger.warning("B站凭证刷新需要 `bili_jct` 和 `ac_time_value`")
            return False

        # 获取 refresh_csrf
        try:
            session = await self._get_session()
            corr_resp = await session.get(f"https://www.bilibili.com/correspond/1/{self._credential.bili_jct}")
            corr_data = corr_resp.json()
            refresh_csrf = corr_data.get("data", {}).get("refresh_csrf", "")
            if not refresh_csrf:
                logger.warning("无法获取 refresh_csrf")
                return False
        except Exception as e:
            logger.warning(f"获取 refresh_csrf 失败: {e}")
            return False

        try:
            resp = await self._post(
                "https://passport.bilibili.com/x/passport-login/web/cookie/refresh",
                data={
                    "csrf": self._credential.bili_jct,
                    "refresh_csrf": refresh_csrf,
                    "refresh_token": self._credential.ac_time_value,
                    "source": "main_web",
                },
            )
            new_cookies = resp.data or {}

            self._credential.sessdata = new_cookies.get("SESSDATA", self._credential.sessdata)
            self._credential.bili_jct = new_cookies.get("bili_jct", self._credential.bili_jct)
            self._credential.dedeuserid = new_cookies.get("DedeUserID", self._credential.dedeuserid)
            new_refresh_token = new_cookies.get("refresh_token") or (resp.data or {}).get("refresh_token")

            if new_refresh_token:
                self._credential.ac_time_value = new_refresh_token

            # 确认刷新
            if self._credential.has_bili_jct():
                await self._post(
                    "https://passport.bilibili.com/x/passport-login/web/cookie/confirm",
                    data={"csrf": self._credential.bili_jct, "refresh_token": self._credential.ac_time_value},
                )
            return True
        except Exception as e:
            logger.warning(f"刷新 B站凭证失败: {e}")
            return False

    # ── 视频 ──

    async def get_video_info(self, *, bvid: str | None = None, aid: int | None = None) -> dict:
        """获取视频信息"""
        params = {}
        if bvid:
            params["bvid"] = bvid
        if aid:
            params["aid"] = aid
        resp = await self._get("https://api.bilibili.com/x/web-interface/view", params=params)
        return resp.data

    async def get_play_url(self, bvid: str, cid: int, *, platform: str = "") -> PlayUrlData:
        """获取视频播放/下载 URL"""
        params: dict = {
            "bvid": bvid,
            "cid": cid,
            "qn": "127",
            "fnval": 4048,
            "fnver": 0,
            "fourk": 1,
            "gaia_source": "pre-load",
            "isGaiaAvoided": "true",
            "from_client": "BROWSER",
            "web_location": 1315873,
        }
        if platform == "html5":
            params["platform"] = platform
            params["high_quality"] = "1"
        else:
            params.pop("web_location")
            params.pop("from_client")
            params.pop("gaia_source")
            params.pop("isGaiaAvoided")

        resp = await self._get(
            "https://api.bilibili.com/x/player/wbi/playurl",
            params=params,
            wbi=True,
        )
        play_data: PlayUrlData = msgspec_json.decode(msgspec_json.encode(resp.data), type=PlayUrlData)
        # 处理番剧包装
        if play_data.video_info:
            play_data = play_data.video_info
        return play_data

    async def get_ai_conclusion(self, bvid: str, cid: int) -> dict:
        """获取 AI 总结"""
        resp = await self._get(
            "https://api.bilibili.com/x/web-interface/view/conclusion",
            params={"bvid": bvid, "cid": cid, "up_mid": ""},
            wbi=True,
        )
        return resp.data

    async def get_cid(self, bvid: str, page_index: int = 0) -> int:
        """获取分 P 的 cid"""
        resp = await self._get(
            "https://api.bilibili.com/x/player/pagelist",
            params={"bvid": bvid},
        )
        if not resp.data:
            raise ParseException("获取分P列表失败")
        pages = resp.data if isinstance(resp.data, list) else []
        if page_index >= len(pages):
            page_index = 0
        return int(pages[page_index]["cid"])

    # ── 动态 ──

    async def get_dynamic_detail(self, dynamic_id: int) -> dict:
        """获取动态详情 (WBI)"""
        resp = await self._get(
            "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail",
            params={
                "id": dynamic_id,
                "timezone_offset": -480,
                "platform": "web",
                "gaia_source": "main_web",
                "features": (
                    "itemOpusStyle,opusBigCover,onlyfansVote,endFooterHidden,decorationCard,onlyfansAssetsV2,ugcDelete"
                ),
                "web_location": "333.1368",
            },
            wbi=True,
        )
        return resp.data

    async def get_opus_detail(self, opus_id: int) -> dict:
        """获取图文动态 (opus) 详情"""
        resp = await self._get(
            "https://api.bilibili.com/x/opus/detail",
            params={"opus_id": opus_id},
        )
        return resp.data

    async def turn_article_to_opus(self, article_id: int) -> int:
        """将专栏转为 opus，返回 opus_id
        通过 x/article/view 获取 dyn_id_str (即 opus_id)
        """
        resp = await self._get(
            "https://api.bilibili.com/x/article/view",
            params={"id": article_id},
        )
        if not resp.data or not resp.data.get("dyn_id_str"):
            raise ParseException("专栏转 Opus 失败: 无法获取 dyn_id")
        return int(resp.data["dyn_id_str"])

    # ── 直播 ──

    async def get_live_room_info(self, room_id: int) -> dict:
        """获取直播房间信息"""
        room_resp = await self._get(
            "https://api.live.bilibili.com/room/v1/Room/get_info",
            params={"room_id": room_id},
        )
        result = room_resp.data or {}
        # 通过 uid 查主播信息
        if uid := result.get("uid"):
            card_resp = await self._get(
                "https://api.bilibili.com/x/web-interface/card",
                params={"mid": uid},
            )
            if card_resp.data and card_resp.data.get("card"):
                card = card_resp.data["card"]
                result["anchor_info"] = {
                    "uname": card.get("name", ""),
                    "face": card.get("face", ""),
                    "uid": uid,
                }
        return result

    async def is_dynamic_article(self, dynamic_id: int) -> bool:
        """判断动态是否是专栏类型"""
        # 先获取动态信息检查 type 字段
        resp = await self._get(
            "https://api.bilibili.com/x/dynamic/identify",
            params={"dynamic_id": dynamic_id},
        )
        if resp.data and isinstance(resp.data, dict):
            return resp.data.get("type", "") == "article"
        return False

    # ── 收藏夹 ──

    async def get_fav_folder_info(self, fid: int) -> dict:
        """获取收藏夹信息"""
        resp = await self._get(
            "https://api.bilibili.com/x/v3/fav/folder/info",
            params={"fid": fid},
        )
        return resp.data

    async def get_fav_resource_list(self, media_id: int, pn: int = 1, ps: int = 20) -> dict:
        """获取收藏夹内容列表 (参数名 media_id, 非 fid)"""
        resp = await self._get(
            "https://api.bilibili.com/x/v3/fav/resource/list",
            params={
                "media_id": media_id,
                "pn": pn,
                "ps": ps,
                "order": "mtime",
                "tid": 0,
                "type": 0,
                "platform": "web",
                "web_location": "333.1387",
            },
        )
        # B站 API 可能返回 data: null (私有收藏夹等)
        return resp.data if resp.data else {"info": None, "medias": None}
