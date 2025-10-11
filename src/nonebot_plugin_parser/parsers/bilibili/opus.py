from collections.abc import Generator
from typing import Any

from msgspec import Struct


class OpusTextNode(Struct, tag="OpusTextNode"):
    """图文动态文本节点"""

    text: str
    """文本内容"""


class OpusImageNode(Struct, tag="OpusImageNode"):
    """图文动态图片节点"""

    url: str
    """图片链接"""
    alt: str | None = None
    """图片描述"""


class OpusAuthor(Struct):
    """图文动态作者信息"""

    name: str
    face: str
    mid: int
    pub_time: str
    pub_ts: int


class OpusImage(Struct):
    """图文动态图片信息"""

    url: str
    # width: int
    # height: int
    # size: float


class OpusPic(Struct):
    """图文动态图片组"""

    pics: list[OpusImage]
    style: int


class OpusText(Struct):
    """图文动态文本"""

    nodes: list[dict[str, Any]]


class OpusParagraph(Struct):
    """图文动态段落"""

    para_type: int
    text: OpusText | None = None
    pic: OpusPic | None = None
    # align: int = 0
    # format: dict[str, Any] | None = None


class OpusContent(Struct):
    """图文动态内容"""

    paragraphs: list[OpusParagraph]


class OpusStat(Struct):
    """图文动态统计"""

    like: dict[str, Any] | None = None
    comment: dict[str, Any] | None = None
    forward: dict[str, Any] | None = None
    favorite: dict[str, Any] | None = None
    coin: dict[str, Any] | None = None


class OpusModule(Struct):
    """图文动态模块"""

    module_type: str
    module_author: OpusAuthor | None = None
    module_content: OpusContent | None = None
    # module_stat: OpusStat | None = None


class Basic(Struct):
    """图文动态基本信息"""

    title: str


class OpusInfo(Struct):
    """图文动态信息"""

    id_str: str
    type: int
    modules: list[OpusModule]
    basic: Basic | None = None


class OpusItem(Struct):
    """图文动态项目"""

    item: OpusInfo

    @property
    def title(self) -> str | None:
        return self.item.basic.title if self.item.basic else None

    @property
    def name_avatar(self) -> tuple[str, str]:
        author_module = next(module.module_author for module in self.item.modules if module.module_author)
        return author_module.name, author_module.face

    @property
    def timestamp(self) -> int | None:
        """获取发布时间戳"""
        for module in self.item.modules:
            if module.module_type == "MODULE_TYPE_AUTHOR" and module.module_author:
                return module.module_author.pub_ts
        return None

    def gen_text_img(self) -> Generator[OpusTextNode | OpusImageNode, None, None]:
        """生成图文节点（保持顺序）"""
        for module in self.item.modules:
            if module.module_type == "MODULE_TYPE_CONTENT" and module.module_content:
                for paragraph in module.module_content.paragraphs:
                    # 处理文本段落
                    if paragraph.text and paragraph.text.nodes:
                        text_content = ""
                        for node in paragraph.text.nodes:
                            if node.get("type") in ["TEXT_NODE_TYPE_WORD", "TEXT_NODE_TYPE_RICH"] and node.get("word"):
                                text_content += node["word"].get("words", "")
                        if text_content.strip():
                            yield OpusTextNode(text=text_content.strip())

                    # 处理图片段落
                    if paragraph.pic and paragraph.pic.pics:
                        for pic in paragraph.pic.pics:
                            yield OpusImageNode(url=pic.url)
