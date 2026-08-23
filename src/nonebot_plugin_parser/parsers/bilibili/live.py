from msgspec import Struct, field


class AnchorInfo(Struct):
    uname: str = ""
    """用户名"""
    face: str = ""
    """头像"""
    uid: int = 0


class RoomData(Struct):
    room_id: int = 0
    uid: int = 0
    raw_title: str = field(default="", name="title")
    """原始标题"""
    cover: str = field(default="", name="user_cover")
    """封面"""
    keyframe: str = ""
    """关键帧"""
    live_status: int = 0
    """直播状态 1=直播中"""
    online: int = 0
    """在线人数"""
    tags: str = ""
    """标签"""
    area_name: str = ""
    """分区名称"""
    parent_area_name: str = ""
    """父分区名称"""
    anchor_info: AnchorInfo | None = None
    """主播信息"""

    @property
    def title(self) -> str:
        return f"直播 - {self.raw_title}"

    @property
    def detail(self) -> str:
        parts = []
        if self.area_name:
            parts.append(f"分区: {self.area_name}")
            if self.parent_area_name:
                parts[-1] += f" | {self.parent_area_name}"
        if self.tags:
            parts.append(f"标签: {self.tags}")
        if self.online:
            parts.append(f"在线: {self.online}")
        return "\n".join(parts) if parts else ""

    @property
    def name(self) -> str:
        return self.anchor_info.uname if self.anchor_info else ""

    @property
    def avatar(self) -> str:
        return self.anchor_info.face if self.anchor_info else ""
