from msgspec import Struct, field
from msgspec.json import Decoder

from .common import Video


class Image(Struct):
    urlDefault: str


class User(Struct):
    nickname: str
    avatar: str


class NoteDetail(Struct):
    type: str
    title: str
    desc: str
    user: User
    imageList: list[Image] = field(default_factory=list)
    video: Video | None = None

    @property
    def nickname(self) -> str:
        return self.user.nickname

    @property
    def avatar_url(self) -> str:
        return self.user.avatar

    @property
    def image_urls(self) -> list[str]:
        return [item.urlDefault for item in self.imageList]

    @property
    def _cover_url(self) -> str | None:
        # 取第一张图片作为封面，如果没有图片则返回 None
        return self.imageList[0].urlDefault if self.imageList else None

    @property
    def is_video(self) -> bool:
        return self.type == "video" and self.video is not None

    @property
    def video_cover_duration(self):
        assert self.video is not None
        video_url, duration = self.video.url_and_duration
        assert video_url is not None
        return video_url, self._cover_url, duration


class NoteDetailWrapper(Struct):
    """Wrapper for note detail, represents the value in noteDetailMap[xhs_id]"""

    note: NoteDetail


class Note(Struct):
    """Top-level note container with noteDetailMap"""

    noteDetailMap: dict[str, NoteDetailWrapper]


class InitialState(Struct):
    """Root structure of window.__INITIAL_STATE__"""

    note: Note


decoder = Decoder(InitialState)
