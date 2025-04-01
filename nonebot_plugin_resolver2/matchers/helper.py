from pathlib import Path

from nonebot import get_bots
from nonebot.adapters.onebot.utils import f2s
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.matcher import Matcher

from ..config import NEED_FORWARD, NICKNAME, USE_BASE64
from ..constant import VIDEO_MAX_MB


def construct_nodes(segments: MessageSegment | list[MessageSegment | Message | str]) -> Message:
    """构造节点

    Args:
        segments (MessageSegment | list[MessageSegment | Message | str]): 消息段

    Returns:
        Message: 消息
    """
    bot = next(iter(bot for bot in get_bots().values() if isinstance(bot, Bot)))
    user_id = int(bot.self_id)

    def node(content):
        return MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME, content=content)

    segments = segments if isinstance(segments, list) else [segments]
    return Message([node(seg) for seg in segments])


async def send_segments(matcher: type[Matcher], segments: list) -> None:
    """发送消息段

    Args:
        matcher (type[Matcher]): 响应器
        segments (list): 消息段
    """
    if NEED_FORWARD or len(segments) > 4:
        await matcher.send(construct_nodes(segments))
    else:
        for seg in segments:
            await matcher.send(seg)


def get_img_seg(img_path: Path) -> MessageSegment:
    """获取图片 Seg

    Args:
        img_path (Path): 图片路径

    Returns:
        MessageSegment: 图片 Seg
    """
    file = img_path.read_bytes() if USE_BASE64 else img_path
    return MessageSegment.image(file)


def get_video_seg(video_path: Path) -> MessageSegment:
    """获取视频 Seg

    Returns:
        MessageSegment: 视频 Seg
    """
    seg: MessageSegment
    # 检测文件大小
    file_size_byte_count = int(video_path.stat().st_size)
    file = video_path.read_bytes() if USE_BASE64 else video_path
    if file_size_byte_count == 0:
        seg = MessageSegment.text("获取视频失败")
    elif file_size_byte_count > VIDEO_MAX_MB * 1024 * 1024:
        # 转为文件 Seg
        seg = get_file_seg(file)
    else:
        seg = MessageSegment.video(file)
    return seg


def get_file_seg(file: Path | bytes, display_name: str = "") -> MessageSegment:
    """获取文件 Seg

    Args:
        file (Path | bytes): 文件路径
        display_name (str, optional): 显示名称. Defaults to file.name.

    Returns:
        MessageSegment: 文件 Seg
    """
    file_name = file.name if isinstance(file, Path) else display_name
    if not file_name:
        raise ValueError("文件名不能为空")
    if USE_BASE64:
        file = file.read_bytes() if isinstance(file, Path) else file

    return MessageSegment(
        "file",
        data={
            "name": file_name,
            "file": f2s(file),
        },
    )
