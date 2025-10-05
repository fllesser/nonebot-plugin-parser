from msgspec import Struct, field

from ..data import ParseData


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

    @property
    def parse_data(self) -> ParseData:
        """转换为ParseData对象"""
        return ParseData(
            title=self.desc,
            name=self.name,
            avatar_url=self.avatar_url,
            timestamp=self.create_time,
            images_urls=self.images_urls,
            dynamic_urls=self.dynamic_urls,
        )


class SlidesInfo(Struct):
    aweme_details: list[SlidesData] = field(default_factory=list)


from ..data import ParseData
