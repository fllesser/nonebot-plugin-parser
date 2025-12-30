import time

from msgspec import Struct
from msgspec.json import Decoder


class User(Struct):
    name: str
    headUrl: str


class Representation(Struct):
    url: str


class AdaptationSet(Struct):
    representation: list[Representation]


class KsPlay(Struct):
    adaptationSet: list[AdaptationSet]


_ks_play_decoder = Decoder(KsPlay)


class CurrentVideoInfo(Struct):
    ksPlayJson: KsPlay | str

    def __post_init__(self):
        # 如果 ksPlayJson 是字符串，则解析为 KsPlay 对象
        if isinstance(self.ksPlayJson, str):
            self.ksPlayJson = _ks_play_decoder.decode(self.ksPlayJson)

    @property
    def representations(self) -> list[Representation]:
        assert isinstance(self.ksPlayJson, KsPlay)
        return self.ksPlayJson.adaptationSet[0].representation


class VideoInfo(Struct, kw_only=True):
    title: str
    description: str
    createTime: str
    user: User
    currentVideoInfo: CurrentVideoInfo

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def avatar_url(self) -> str:
        return self.user.headUrl

    @property
    def text(self) -> str:
        return f"简介: {self.description}"

    @property
    def timestamp(self) -> int:
        return int(time.mktime(time.strptime(self.createTime, "%Y-%m-%d")))

    @property
    def m3u8s_url(self) -> str:
        representations = self.currentVideoInfo.representations
        # 这里[d.url for d in representations]，从 4k ~ 360，此处默认720p
        return [d.url for d in representations][3]


decoder = Decoder(VideoInfo)
