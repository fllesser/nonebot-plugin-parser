from msgspec import Struct, field


class PlayAddr(Struct):
    url_list: list[str]


class Cover(Struct):
    url_list: list[str]


class Video(Struct):
    play_addr: PlayAddr
    cover: Cover
    duration: int


class Image(Struct):
    video: Video | None = None
    url_list: list[str] = field(default_factory=list)


class Avatar(Struct):
    url_list: list[str]


class Author(Struct):
    nickname: str
    avatar_larger: Avatar


class SlidesData(Struct):
    author: Author
    desc: str
    create_time: int
    images: list[Image]

    @property
    def name(self) -> str:
        return self.author.nickname

    @property
    def avatar_url(self) -> str:
        from random import choice

        return choice(self.author.avatar_larger.url_list)

    @property
    def images_urls(self) -> list[str]:
        return [image.url_list[0] for image in self.images]

    @property
    def dynamic_urls(self) -> list[str]:
        return [image.video.play_addr.url_list[0] for image in self.images if image.video]


class SlidesInfo(Struct):
    aweme_details: list[SlidesData] = field(default_factory=list)


from ..data import TransitionData


class SlidesTransitionData(TransitionData):
    def __init__(self, slides_data: SlidesData):
        self.slides_data = slides_data

    def name_avatar_desc(self) -> tuple[str, str | None, str | None]:
        return self.slides_data.name, self.slides_data.avatar_url, self.slides_data.desc

    def get_title(self) -> str:
        return self.slides_data.desc

    def get_images_urls(self) -> list[str] | None:
        return self.slides_data.images_urls

    def get_dynamic_urls(self) -> list[str] | None:
        return self.slides_data.dynamic_urls

    def get_timestamp(self) -> int | None:
        return self.slides_data.create_time
