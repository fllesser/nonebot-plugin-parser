from msgspec import Struct, field
from msgspec.json import Decoder


class Addr(Struct):
    uri: str

    @property
    def url(self) -> str:
        return f"https://aweme.snssdk.com/aweme/v1/play/?video_id={self.uri}&ratio=1080p&line=0"


class UrlList(Struct):
    url_list: list[str]


class Author(Struct):
    uid: str
    nickname: str
    avatar_thumb: UrlList
    """头像"""
    signature: str | None = None


class Video(Struct):
    cover: UrlList
    duration: int
    """视频时长(/1000)"""
    play_addr: Addr
    cover_original_scale: UrlList | None = None

    @property
    def url(self) -> str:
        return self.play_addr.url


class Image(Struct):
    url_list: list[str]
    uri: str = field(default="")
    clip_type: int | None = field(default=None)
    """=2 or None 是普通图片"""
    video: Video | None = field(default=None)
    """Live Photo 视频"""


class MusicPlayUrl(Struct):
    uri: str


class Music(Struct):
    duration: int
    mid: str
    play_url: MusicPlayUrl
    extra: str
    is_original_sound: bool


class ShareInfo(Struct):
    share_desc: str
    share_desc_info: str

    @property
    def text(self) -> str:
        return self.share_desc_info.replace(f"#{self.share_desc}#", "", 1)


class Aweme(Struct):
    aweme_id: str
    author: Author
    share_info: ShareInfo
    create_time: int
    share_url: str
    images: list[Image] | None = field(default=None)
    music: Music | None = field(default=None)
    video: Video | None = field(default=None)


class Response(Struct):
    aweme_detail: Aweme


decoder = Decoder(Response)
