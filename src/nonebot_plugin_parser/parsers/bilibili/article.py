"""Bilibili 专栏文章解析器"""

from collections.abc import Generator
from typing import Any, Union

from pydantic import BaseModel


class Category(BaseModel):
    """分类信息"""

    id: int
    parent_id: int
    name: str


class Pendant(BaseModel):
    """头像挂件"""

    pid: int
    name: str
    image: str
    expire: int


class OfficialVerify(BaseModel):
    """官方认证"""

    type: int
    desc: str


class Nameplate(BaseModel):
    """成就徽章"""

    nid: int
    name: str
    image: str
    image_small: str
    level: str
    condition: str


class VipLabel(BaseModel):
    """VIP标签"""

    path: str
    text: str
    label_theme: str


class Vip(BaseModel):
    """VIP信息"""

    type: int
    status: int
    due_date: int
    vip_pay_type: int
    theme_type: int
    label: VipLabel
    avatar_subscript: int
    nickname_color: str


class Author(BaseModel):
    """作者信息"""

    mid: int
    name: str
    face: str
    pendant: Pendant
    official_verify: OfficialVerify
    nameplate: Nameplate
    vip: Vip
    fans: int
    level: int


class Stats(BaseModel):
    """统计信息"""

    view: int
    favorite: int
    like: int
    dislike: int
    reply: int
    share: int
    coin: int
    dynamic: int


class Tag(BaseModel):
    """标签"""

    tid: int
    name: str


class Media(BaseModel):
    """媒体信息"""

    score: int
    media_id: int
    title: str
    cover: str
    area: str
    type_id: int
    type_name: str
    spoiler: int
    season_id: int


class ArticleMeta(BaseModel):
    """文章元信息"""

    id: int
    category: Category
    categories: list[Category]
    title: str
    summary: str
    banner_url: str
    template_id: int
    state: int
    author: Author
    reprint: int
    image_urls: list[str]
    publish_time: int
    ctime: int
    mtime: int
    stats: Stats
    tags: list[Tag]
    words: int
    dynamic: str
    origin_image_urls: list[str]
    list: Any = None
    is_like: bool
    media: Media
    apply_time: str
    check_time: str
    original: int
    act_id: int
    dispute: Any = None
    authenMark: Any = None
    cover_avid: int
    top_video_info: Any = None
    type: int
    check_state: int
    origin_template_id: int
    private_pub: int
    content_pic_list: Any = None
    keywords: str
    version_id: int
    dyn_id_str: str
    total_art_num: int


class TextNode(BaseModel):
    """文本节点"""

    type: str = "TextNode"
    text: str = ""


class BoldNode(BaseModel):
    """粗体节点"""

    type: str = "BoldNode"
    children: list[Union["TextNode", "FontSizeNode", "BoldNode"]] = []


class FontSizeNode(BaseModel):
    """字体大小节点"""

    type: str = "FontSizeNode"
    size: int = 0
    children: list[Union["TextNode", "BoldNode", "FontSizeNode"]] = []


class ColorNode(BaseModel):
    """颜色节点"""

    type: str = "ColorNode"
    color: str = ""
    children: list["TextNode"] = []


class ParagraphNode(BaseModel):
    """段落节点"""

    type: str = "ParagraphNode"
    children: list[TextNode | BoldNode | FontSizeNode | ColorNode] = []


class ImageNode(BaseModel):
    """图片节点"""

    type: str = "ImageNode"
    url: str = ""
    alt: str = ""


class VideoCardNode(BaseModel):
    """视频卡片节点"""

    type: str = "VideoCardNode"
    aid: int = 0


class ArticleChild(BaseModel):
    """文章子节点"""

    type: str
    children: list[TextNode | BoldNode | FontSizeNode | ColorNode | ParagraphNode] = []
    url: str = ""
    alt: str = ""
    aid: int = 0


class ArticleInfo(BaseModel):
    """文章信息"""

    type: str = "Article"
    meta: ArticleMeta
    children: list[ArticleChild]

    def extract_text_from_node(self, node: TextNode | BoldNode | FontSizeNode | ColorNode) -> str:
        """从节点中提取文本内容"""
        if isinstance(node, TextNode):
            return node.text
        elif isinstance(node, (BoldNode, FontSizeNode, ColorNode)):
            text = ""
            for child in node.children:
                text += self.extract_text_from_node(child)
            return text
        return ""

    def extract_text_from_paragraph(self, paragraph: ParagraphNode) -> str:
        """从段落中提取文本内容"""
        text = ""
        for child in paragraph.children:
            text += self.extract_text_from_node(child)
        return text.strip()

    def gen_text_img(self) -> Generator[TextNode | ImageNode, None, None]:
        """生成文本和图片节点（保持顺序）"""
        for child in self.children:
            if child.type == "ParagraphNode":
                # 处理段落节点，直接提取文本内容
                text_content = self._extract_text_from_children(child.children)
                if text_content.strip():
                    yield TextNode(text=text_content)
            elif child.type == "ImageNode":
                # 处理图片节点
                yield ImageNode(url=child.url, alt=child.alt)
            elif child.type == "VideoCardNode":
                # 处理视频卡片节点（转换为文本描述）
                yield TextNode(text=f"[视频卡片: {child.aid}]")

    def _extract_text_from_children(self, children: list) -> str:
        """从子节点列表中提取文本内容"""
        text_content = ""
        for child in children:
            if isinstance(child, dict):
                # 处理原始字典数据
                if child.get("type") == "TextNode":
                    text_content += child.get("text", "")
                elif child.get("type") in ["BoldNode", "FontSizeNode", "ColorNode", "ParagraphNode"]:
                    # 递归处理嵌套节点
                    text_content += self._extract_text_from_children(child.get("children", []))
            elif hasattr(child, "type"):
                # 处理 Pydantic 对象
                if child.type == "TextNode":
                    text_content += getattr(child, "text", "")
                elif child.type in ["BoldNode", "FontSizeNode", "ColorNode", "ParagraphNode"]:
                    # 递归处理嵌套节点
                    text_content += self._extract_text_from_children(getattr(child, "children", []))
        return text_content

    def get_author_info(self) -> tuple[str, str]:
        """获取作者信息"""
        return self.meta.author.name, self.meta.author.face

    def get_title(self) -> str:
        """获取标题"""
        return self.meta.title

    def get_timestamp(self) -> int:
        """获取发布时间戳"""
        return self.meta.publish_time

    def get_summary(self) -> str:
        """获取摘要"""
        return self.meta.summary

    def get_stats(self) -> Stats:
        """获取统计信息"""
        return self.meta.stats

    def get_tags(self) -> list[str]:
        """获取标签列表"""
        return [tag.name for tag in self.meta.tags]


# 更新前向引用
BoldNode.model_rebuild()
FontSizeNode.model_rebuild()
ParagraphNode.model_rebuild()
ArticleChild.model_rebuild()
