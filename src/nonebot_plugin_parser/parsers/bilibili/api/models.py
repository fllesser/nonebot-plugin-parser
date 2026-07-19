"""Bilibili API 响应模型 — 仅保留实际使用的类型"""

from __future__ import annotations

from typing import Any

from msgspec import Struct, field


class ApiResponse(Struct, kw_only=True):
    """B站 API 通用响应包装"""

    code: int = 0
    message: str = ""
    data: Any = None


class WbiImg(Struct, kw_only=True):
    """WBI 签名图片"""

    img_url: str = ""
    sub_url: str = ""


class NavData(Struct, kw_only=True):
    """导航栏信息 (用于 wbi key 和登录状态)"""

    isLogin: bool = False
    wbi_img: WbiImg | None = None
    face: str = ""
    uname: str = ""


class DashVideoStream(Struct, kw_only=True):
    """DASH 视频流"""

    id: int = 0
    base_url: str = ""
    backup_url: list[str] | None = None
    bandwidth: int = 0
    codecs: str = ""
    frame_rate: str = ""
    width: int = 0
    height: int = 0
    sar: str = ""
    mime_type: str = ""
    segment_base: dict[str, Any] = field(default_factory=dict)


class DashAudioStream(Struct, kw_only=True):
    """DASH 音频流"""

    id: int = 0
    base_url: str = ""
    backup_url: list[str] | None = None
    bandwidth: int = 0
    codecs: str = ""
    mime_type: str = ""


class DashData(Struct, kw_only=True):
    """DASH 数据"""

    video: list[DashVideoStream] = field(default_factory=list)
    audio: list[DashAudioStream] | None = None
    dolby: dict[str, Any] | None = None
    flac: dict[str, Any] | None = None


class DurlItem(Struct, kw_only=True):
    """FLV/MP4 直链"""

    url: str = ""
    backup_url: list[str] | None = None


class PlayUrlData(Struct, kw_only=True):
    """播放 URL 接口返回 data"""

    dash: DashData | None = None
    durl: list[DurlItem] | None = None
    format: str = ""
    quality: int = 0
    video_codecid: int = 0
    video_info: PlayUrlData | None = None  # bangumi 包装
