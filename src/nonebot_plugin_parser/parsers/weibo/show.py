from re import sub

from msgspec import Struct
from msgspec.json import Decoder


class User(Struct):
    name: str
    profile_image_url: str
    description: str


class Reward(Struct):
    user: User


class PlayInfo(Struct):
    title: str
    text: str
    reward: Reward
    cover_image: str
    stream_url: str
    real_date: int
    urls: dict[str, str]

    @property
    def name(self) -> str:
        return self.reward.user.name

    @property
    def avatar(self) -> str:
        return self.reward.user.profile_image_url

    @property
    def description(self) -> str:
        return self.reward.user.description

    @property
    def clean_text(self) -> str:
        text = sub(r"<[^>]*>", "", self.text)
        return text.replace("\n\n", "").strip()

    @property
    def cover_url(self) -> str:
        return "https:" + self.cover_image

    @property
    def video_url(self) -> str:
        url = next(iter(self.urls.values()), None)
        return "https:" + url if url else self.stream_url


class Data(Struct):
    Component_Play_Playinfo: PlayInfo


class DataWrapper(Struct):
    data: Data


decoder = Decoder(DataWrapper)
