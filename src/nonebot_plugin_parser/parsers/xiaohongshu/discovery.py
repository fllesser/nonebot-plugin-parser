from msgspec import Struct
from msgspec.json import Decoder

from .common import Video


class Image(Struct):
    url: str
    urlSizeLarge: str | None = None


class User(Struct):
    nickName: str
    avatar: str


class NoteData(Struct):
    type: str
    title: str
    desc: str
    user: User
    time: int
    lastUpdateTime: int
    imageList: list[Image] = []  # 有水印
    video: Video | None = None

    @property
    def image_urls(self) -> list[str]:
        return [item.url for item in self.imageList]

    @property
    def video_url(self) -> str | None:
        if self.type != "video" or not self.video:
            return None
        return self.video.video_url


class NormalNotePreloadData(Struct):
    title: str
    desc: str
    imagesList: list[Image] = []  # 无水印, 但只有一只，用于视频封面

    @property
    def image_urls(self) -> list[str]:
        return [item.urlSizeLarge or item.url for item in self.imagesList]


class NoteDataWrapper(Struct):
    noteData: NoteData


class NoteDataContainer(Struct):
    data: NoteDataWrapper
    normalNotePreloadData: NormalNotePreloadData | None = None


class InitialState(Struct):
    noteData: NoteDataContainer


decoder = Decoder(InitialState)
