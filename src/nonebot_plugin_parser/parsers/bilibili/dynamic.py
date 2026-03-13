from typing import Any

from msgspec import Struct, field, convert


class AuthorInfo(Struct):
    """作者信息"""

    name: str
    face: str
    mid: int
    pub_time: str
    pub_ts: int
    # jump_url: str
    # following: bool = False
    # official_verify: dict[str, Any] | None = None
    # vip: dict[str, Any] | None = None
    # pendant: dict[str, Any] | None = None


class VideoArchive(Struct):
    """视频信息"""

    aid: str
    bvid: str
    title: str
    desc: str
    cover: str
    duration_text: str = ""
    # jump_url: str
    # stat: dict[str, str]
    # badge: dict[str, Any] | None = None

    @property
    def duration_seconds(self) -> float:
        """将 duration_text（如 '3:42'）解析为秒数"""
        if not self.duration_text:
            return 0.0
        parts = self.duration_text.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            pass
        return 0.0


class OpusImage(Struct):
    """图文动态图片信息"""

    url: str
    # width: int
    # height: int
    # size: float
    # aigc: dict[str, Any] | None = None
    # live_url: str | None = None


class OpusSummary(Struct):
    """图文动态摘要"""

    text: str
    # rich_text_nodes: list[dict[str, Any]]


class OpusContent(Struct):
    """图文动态内容"""

    jump_url: str
    pics: list[OpusImage]
    summary: OpusSummary
    title: str | None = None
    # fold_action: list[str] | None = None


class DynamicMajor(Struct):
    """动态主要内容"""

    type: str | None = None
    archive: VideoArchive | None = None
    opus: OpusContent | None = None
    desc: OpusSummary | None = None

    @property
    def title(self) -> str | None:
        """获取标题"""
        if self.type == "MAJOR_TYPE_ARCHIVE" and self.archive:
            return self.archive.title
        if self.type == "MAJOR_TYPE_OPUS" and self.opus:
            return self.opus.title
        return None

    @property
    def text(self) -> str | None:
        """获取文本内容"""
        if self.type == "MAJOR_TYPE_ARCHIVE" and self.archive:
            return self.archive.desc
        elif self.type == "MAJOR_TYPE_OPUS" and self.opus:
            return self.opus.summary.text
        elif self.desc:
            return self.desc.text
        return None

    @property
    def image_urls(self) -> list[str]:
        """获取图片URL列表"""
        if self.type == "MAJOR_TYPE_OPUS" and self.opus:
            return [pic.url for pic in self.opus.pics]
        elif self.type == "MAJOR_TYPE_ARCHIVE" and self.archive and self.archive.cover:
            return [self.archive.cover]
        return []

    @property
    def cover_url(self) -> str | None:
        """获取封面URL"""
        if self.type == "MAJOR_TYPE_ARCHIVE" and self.archive:
            return self.archive.cover
        return None

    @property
    def duration(self) -> float:
        """获取视频时长（秒）"""
        if self.type == "MAJOR_TYPE_ARCHIVE" and self.archive:
            return self.archive.duration_seconds
        return 0.0


class DynamicModule(Struct):
    """动态模块"""

    module_author: AuthorInfo
    module_dynamic: dict[str, Any] | None = None
    module_stat: dict[str, Any] | None = None

    _cached_major: DynamicMajor | None = field(default=None)

    @property
    def author_name(self) -> str:
        """获取作者名称"""
        return self.module_author.name

    @property
    def author_face(self) -> str:
        """获取作者头像URL"""
        return self.module_author.face

    @property
    def pub_ts(self) -> int:
        """获取发布时间戳"""
        return self.module_author.pub_ts

    @property
    def _major_info(self) -> dict[str, Any] | None:
        """获取主要内容信息"""
        if self.module_dynamic:
            if major := self.module_dynamic.get("major"):
                return major
            # 转发类型动态没有 major
            return self.module_dynamic
        return None

    @property
    def major(self) -> DynamicMajor | None:
        """获取缓存的 DynamicMajor 实例"""
        if self._cached_major is None:
            major_info = self._major_info
            if major_info:
                self._cached_major = convert(major_info, DynamicMajor)
        return self._cached_major

    @property
    def desc_text(self) -> str | None:
        """获取动态自身的文字描述（非 major 内容的文字）"""
        if self.module_dynamic:
            desc = self.module_dynamic.get("desc")
            if desc and isinstance(desc, dict):
                return desc.get("text")
        return None


class DynamicInfo(Struct):
    """动态信息"""

    id_str: str
    type: str
    visible: bool
    modules: DynamicModule
    basic: dict[str, Any] | None = None
    orig: "DynamicInfo | None" = None

    @property
    def name(self) -> str:
        """获取作者名称"""
        return self.modules.author_name

    @property
    def avatar(self) -> str:
        """获取作者头像URL"""
        return self.modules.author_face

    @property
    def timestamp(self) -> int:
        """获取发布时间戳"""
        return self.modules.pub_ts

    @property
    def title(self) -> str | None:
        """获取标题"""
        if major := self.modules.major:
            return major.title

    @property
    def text(self) -> str | None:
        """获取文本内容（优先取动态自身文字，回退到 major 的文字）"""
        # 优先取动态自身描述（如发视频时附带的文字）
        if desc_text := self.modules.desc_text:
            return desc_text
        # 回退到 major 的文字（图文摘要、视频简介等）
        if major := self.modules.major:
            return major.text

    @property
    def image_urls(self) -> list[str]:
        """获取图片URL列表"""
        if major := self.modules.major:
            return major.image_urls
        return []

    def is_video(self) -> bool:
        """判断是否为视频动态"""
        major = self.modules.major
        return major is not None and major.archive is not None


class DynamicData(Struct):
    """动态项目"""

    item: DynamicInfo
