from msgspec import Struct
from msgspec.json import Decoder


class User(Struct):
    name: str
    headUrl: str


class Representation(Struct):
    url: str
    qualityType: str


class AdaptationSet(Struct):
    representation: list[Representation]


class KsPlay(Struct):
    adaptationSet: list[AdaptationSet]


_ks_play_decoder = Decoder(KsPlay)


class CurrentVideoInfo(Struct):
    ksPlayJson: KsPlay | str
    durationMillis: int

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
    description: str | None
    createTimeMillis: int
    user: User
    currentVideoInfo: CurrentVideoInfo
    coverUrl: str

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def avatar_url(self) -> str:
        return self.user.headUrl

    @property
    def text(self) -> str | None:
        return f"简介: {self.description}" if self.description else None

    @property
    def timestamp(self) -> int:
        return self.createTimeMillis // 1000

    @property
    def duration(self) -> int:
        return self.currentVideoInfo.durationMillis // 1000

    @property
    def m3u8s_url(self) -> str:
        representations = self.currentVideoInfo.representations

        quality_types = ("1080p", "720p", "480p", "360p")
        for r in representations:
            if r.qualityType in quality_types:
                return r.url

        return representations[0].url


decoder = Decoder(VideoInfo)
