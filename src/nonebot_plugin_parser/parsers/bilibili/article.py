from collections.abc import Generator, Sequence
from typing import Any

from msgspec import Struct

from .common import Upper


class Stats(Struct):
    view: int
    """浏览量"""
    favorite: int
    """收藏数"""
    like: int
    """点赞数"""
    reply: int
    """回复数"""
    share: int
    """分享数"""
    coin: int
    """硬币数"""
    dynamic: int
    """动态数"""


class TextNode(Struct, tag="TextNode"):
    text: str
    """文本内容"""


class ImageNode(Struct, tag="ImageNode"):
    url: str
    """图片链接"""
    alt: str | None = None
    """图片描述"""


class VideoCardNode(Struct, tag="VideoCardNode"):
    aid: int
    """视频ID"""


class BoldNode(Struct, tag="BoldNode"):
    children: list[TextNode] = []
    """子节点"""


class FontSizeNode(Struct, tag="FontSizeNode"):
    size: int
    """字体大小"""
    children: list[TextNode | BoldNode | Any] = []
    """子节点"""


class ColorNode(Struct, tag="ColorNode"):
    color: str
    """颜色值"""
    children: list[TextNode] = []
    """子节点"""


class ParagraphNode(Struct, tag="ParagraphNode"):
    children: list[FontSizeNode | ColorNode | BoldNode] = []
    """子节点"""


FinalChild = TextNode | ImageNode | VideoCardNode
Child = FontSizeNode | ColorNode | BoldNode | ParagraphNode


class MetaData(Struct):
    title: str
    """标题"""
    summary: str
    """摘要"""
    banner_url: str
    """封面"""
    author: Upper
    """作者"""
    publish_time: int
    """发布时间戳"""
    ctime: int
    """创建时间戳"""
    mtime: int
    """修改时间戳"""
    stats: Stats
    """统计信息"""
    words: int
    """字数"""


class ArticleInfo(Struct):
    type: str
    """类型"""
    meta: MetaData
    """元数据"""
    children: list[Child | FinalChild]
    """子节点"""

    @property
    def foreach_children(self):
        for child in self.children:
            if isinstance(child, FinalChild):
                yield child
            elif isinstance(child, Child):
                yield from child.children

    def gen_text_img(self) -> Generator[FinalChild, None, None]:
        yield from self._gen_text_img(self.children)

    @classmethod
    def _gen_text_img(cls, children: Sequence[Child | FinalChild]) -> Generator[FinalChild, None, None]:
        for child in children:
            if isinstance(child, ImageNode):
                yield child
            elif isinstance(child, TextNode):
                yield child
            elif isinstance(child, Child | ParagraphNode):
                yield from cls._gen_text_img(child.children)
