from msgspec import Struct


class Upper(Struct):
    mid: int
    """用户 ID"""
    name: str
    """作者"""
    face: str
    """头像"""
