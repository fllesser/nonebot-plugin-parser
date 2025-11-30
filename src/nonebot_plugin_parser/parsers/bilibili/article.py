"""Bilibili 专栏文章解析器"""

from typing import Any
from collections.abc import Generator

from msgspec import Struct


class TextNode(Struct):
    """文本节点"""

    text: str


class ImageNode(Struct):
    """图片节点"""

    url: str
    alt: str | None = None


class Author(Struct):
    """作者信息"""

    mid: int
    name: str
    face: str
    fans: int
    level: int


class Stats(Struct):
    """统计信息"""

    view: int
    favorite: int
    like: int
    reply: int
    share: int
    coin: int


class Meta(Struct):
    """文章元信息"""

    id: int
    title: str
    summary: str
    publish_time: int
    author: Author
    stats: Stats
    tags: list[dict[str, Any]]
    words: int


class ArticleInfo(Struct):
    """文章信息"""

    type: str
    meta: Meta
    children: list[dict[str, Any]]

    def gen_text_img(self) -> Generator[TextNode | ImageNode, None, None]:
        """生成文本和图片节点（保持顺序）"""
        for child in self.children:
            if child.get("type") == "ParagraphNode":
                # 处理段落节点，提取所有文本内容
                text_content = self._extract_text_from_children(child.get("children", []))
                text_content = text_content.strip()
                if text_content:
                    yield TextNode(text="\n\n" + text_content)
            elif child.get("type") == "ImageNode":
                # 处理图片节点
                yield ImageNode(url=child.get("url", ""), alt=child.get("alt"))
            elif child.get("type") == "VideoCardNode":
                # 处理视频卡片节点（转换为文本描述）
                yield TextNode(text=f"\n                         [视频卡片: {child.get('aid', 0)}]")

    def _extract_text_from_children(self, children: list[dict[str, Any]]) -> str:
        """从子节点列表中提取文本内容"""
        text_content = ""
        for child in children:
            if child.get("type") == "TextNode":
                text_content += child.get("text", "")
            elif child.get("type") in ["BoldNode", "FontSizeNode", "ColorNode"]:
                # 递归处理嵌套节点
                text_content += self._extract_text_from_children(child.get("children", []))
        return text_content

    @property
    def author_info(self) -> tuple[str, str]:
        """获取作者信息"""
        return self.meta.author.name, self.meta.author.face

    @property
    def title(self) -> str:
        """获取标题"""
        return self.meta.title

    @property
    def timestamp(self) -> int:
        """获取发布时间戳"""
        return self.meta.publish_time

    @property
    def summary(self) -> str:
        """获取摘要"""
        return self.meta.summary

    @property
    def stats(self) -> Stats:
        """获取统计信息"""
        return self.meta.stats

    @property
    def tags(self) -> list[str]:
        """获取标签列表"""
        return [tag.get("name", "") for tag in self.meta.tags]
