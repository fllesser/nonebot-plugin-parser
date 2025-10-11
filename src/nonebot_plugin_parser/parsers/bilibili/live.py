from msgspec import Struct


class RoomInfo(Struct):
    title: str
    """标题"""
    cover: str
    """封面"""
    keyframe: str
    """关键帧"""
    tags: str
    """标签"""
    area_name: str
    """分区名称"""
    parent_area_name: str
    """父分区名称"""


class BaseInfo(Struct):
    uname: str
    """用户名"""
    face: str
    """头像"""
    gender: str
    """性别"""


class LiveInfo(Struct):
    level: int
    """等级"""
    level_color: int
    """等级颜色"""
    score: int
    """分数"""


class AnchorInfo(Struct):
    base_info: BaseInfo
    """基础信息"""
    live_info: LiveInfo
    """直播信息"""


class RoomData(Struct):
    room_info: RoomInfo
    """房间信息"""
    anchor_info: AnchorInfo
    """主播信息"""

    @property
    def title(self) -> str:
        return f"直播 - {self.room_info.title}"

    @property
    def cover(self) -> str:
        return self.room_info.cover

    @property
    def detail(self) -> str:
        return f"分区: {self.room_info.area_name} | {self.room_info.parent_area_name}\n标签: {self.room_info.tags}"

    @property
    def keyframe(self) -> str:
        return self.room_info.keyframe

    @property
    def name(self) -> str:
        return self.anchor_info.base_info.uname

    @property
    def avatar(self) -> str:
        return self.anchor_info.base_info.face
