from msgspec import Struct

from .common import Upper


class FavItem(Struct):
    title: str
    cover: str
    intro: str
    link: str

    @property
    def url(self) -> str:
        """完整链接"""
        return self.link.replace("bilibili://video/", "https://bilibili.com/video/av")

    @property
    def desc(self) -> str:
        """描述"""
        return f"标题: {self.title}\n简介: {self.intro}\n链接: {self.url}"

    @property
    def avid(self) -> int:
        """avid"""
        return int(self.link.split("/")[-1])


class FavInfo(Struct):
    # id: int
    # fid: int
    # mid: int
    title: str
    """标题"""
    cover: str
    """封面"""
    upper: Upper
    """up 主信息"""
    ctime: int
    """创建时间戳"""
    mtime: int
    """修改时间戳"""
    media_count: int
    """媒体数量"""
    intro: str
    """简介"""


class FavData(Struct):
    info: FavInfo
    medias: list[FavItem]

    @property
    def title(self) -> str:
        return f"收藏夹 - {self.info.title}"

    @property
    def cover(self) -> str:
        return self.info.cover

    @property
    def desc(self) -> str:
        return f"简介: {self.info.intro}"

    @property
    def timestamp(self) -> int:
        return self.info.ctime
