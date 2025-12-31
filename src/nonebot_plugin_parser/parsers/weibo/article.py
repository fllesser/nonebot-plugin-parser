from msgspec import Struct, json


class UserInfo(Struct):
    screen_name: str
    profile_image_url: str


class Data(Struct):
    url: str
    title: str
    content: str
    userinfo: UserInfo
    create_at_unix: int


class Detail(Struct):
    code: str
    msg: str
    data: Data


decoder = json.Decoder(Detail)
