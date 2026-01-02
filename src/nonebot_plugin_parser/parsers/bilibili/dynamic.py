from typing import Any, Optional

from msgspec import Struct, convert


class AuthorInfo(Struct):
    """作者信息"""

    name: str
    face: str
    mid: int
    pub_time: str
    pub_ts: int


class VideoArchive(Struct):
    """视频信息"""

    aid: str
    bvid: str
    title: str
    desc: str
    cover: str


class OpusImage(Struct):
    """图文动态图片信息"""

    url: str


class OpusSummary(Struct):
    """图文动态摘要"""

    text: str


class OpusContent(Struct):
    """图文动态内容"""

    jump_url: str
    pics: list[OpusImage]
    summary: OpusSummary
    title: str | None = None


class DynamicMajor(Struct):
    """动态主要内容 (Major)"""

    type: str
    archive: VideoArchive | None = None
    opus: OpusContent | None = None

    @property
    def title(self) -> str | None:
        """获取标题"""
        if self.type == "MAJOR_TYPE_ARCHIVE" and self.archive:
            return self.archive.title
        return None

    @property
    def text(self) -> str | None:
        """获取文本内容"""
        if self.type == "MAJOR_TYPE_ARCHIVE" and self.archive:
            return self.archive.desc
        elif self.type == "MAJOR_TYPE_OPUS" and self.opus:
            return self.opus.summary.text
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


class DynamicModule(Struct):
    """动态模块"""

    module_author: AuthorInfo
    module_dynamic: dict[str, Any] | None = None
    module_stat: dict[str, Any] | None = None

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
    def major_info(self) -> dict[str, Any] | None:
        """获取主要内容信息"""
        if self.module_dynamic:
            return self.module_dynamic.get("major")
        return None


class DynamicInfo(Struct):
    """动态信息"""

    id_str: str
    type: str
    visible: bool
    modules: DynamicModule
    basic: dict[str, Any] | None = None
    # 【关键修改】添加 orig 字段以支持转发内容 (递归结构)
    orig: Optional["DynamicInfo"] = None

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
        major_info = self.modules.major_info
        if major_info:
            major = convert(major_info, DynamicMajor)
            return major.title
        # 如果是转发动态且没有 major title，可以返回默认值
        if self.type == "DYNAMIC_TYPE_FORWARD":
            return "转发动态"
        return None

    @property
    def text(self) -> str | None:
        """获取文本内容"""
        # 【关键修改】优先从 modules.module_dynamic.desc.text 获取
        # 这是用户发布的文字（包括转发时的评论）
        if self.modules.module_dynamic:
            desc = self.modules.module_dynamic.get("desc")
            if desc and isinstance(desc, dict):
                text_content = desc.get("text")
                if text_content:
                    return text_content

        # 如果没有直接的 desc 文本，尝试从 major 中获取 (例如纯视频投稿的简介)
        major_info = self.modules.major_info
        if major_info:
            major = convert(major_info, DynamicMajor)
            return major.text
            
        return None

    @property
    def image_urls(self) -> list[str]:
        """获取图片URL列表"""
        major_info = self.modules.major_info
        if major_info:
            major = convert(major_info, DynamicMajor)
            return major.image_urls
        return []

    @property
    def cover_url(self) -> str | None:
        """获取封面URL"""
        major_info = self.modules.major_info
        if major_info:
            major = convert(major_info, DynamicMajor)
            return major.cover_url
        return None


class DynamicData(Struct):
    """动态项目"""

    item: DynamicInfo
