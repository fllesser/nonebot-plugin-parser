from re import sub

from msgspec import Struct, json


class LargeInPic(Struct):
    url: str


class Pic(Struct):
    url: str
    large: LargeInPic


class Urls(Struct):
    mp4_720p_mp4: str | None = None
    mp4_hd_mp4: str | None = None
    mp4_ld_mp4: str | None = None

    def get_video_url(self) -> str | None:
        return self.mp4_720p_mp4 or self.mp4_hd_mp4 or self.mp4_ld_mp4 or None


class PagePic(Struct):
    url: str


class PageInfo(Struct):
    title: str | None = None
    urls: Urls | None = None
    page_pic: PagePic | None = None


class User(Struct):
    id: int
    screen_name: str
    """用户昵称"""
    profile_image_url: str
    """头像"""


class WeiboData(Struct):
    user: User
    text: str
    # source: str  # 如 微博网页版
    # region_name: str | None = None

    bid: str
    created_at: str
    """发布时间 格式: `Thu Oct 02 14:39:33 +0800 2025`"""

    status_title: str | None = None
    pics: list[Pic] | None = None
    page_info: PageInfo | None = None
    retweeted_status: "WeiboData | None" = None  # 转发微博

    @property
    def title(self) -> str | None:
        return self.page_info.title if self.page_info else None

    @property
    def display_name(self) -> str:
        return self.user.screen_name

    @property
    def text_content(self) -> str:
        # 将 <br /> 转换为 \n
        text = self.text.replace("<br />", "\n")
        # 去除 html 标签
        text = sub(r"<[^>]*>", "", text)
        return text

    @property
    def cover_url(self) -> str | None:
        if self.page_info is None:
            return None
        if self.page_info.page_pic:
            return self.page_info.page_pic.url
        return None

    @property
    def video_url(self) -> str | None:
        if self.page_info and self.page_info.urls:
            return self.page_info.urls.get_video_url()
        return None

    @property
    def image_urls(self) -> list[str]:
        if self.pics:
            return [x.large.url for x in self.pics]
        return []

    @property
    def url(self) -> str:
        return f"https://weibo.com/{self.user.id}/{self.bid}"

    @property
    def timestamp(self) -> int:
        from time import mktime, strptime

        create_at = strptime(self.created_at, "%a %b %d %H:%M:%S %z %Y")
        return int(mktime(create_at))


class WeiboResponse(Struct):
    ok: int
    data: WeiboData


decoder = json.Decoder(WeiboResponse)
