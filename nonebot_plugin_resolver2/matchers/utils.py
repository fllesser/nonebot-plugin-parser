from pathlib import Path

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.matcher import Matcher

from nonebot_plugin_resolver2.config import NEED_FORWARD, NICKNAME
from nonebot_plugin_resolver2.constant import VIDEO_MAX_MB


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


def get_video_seg(video_path: Path) -> MessageSegment:
    """获取视频 Seg

    Args:
        video_path (Path): 视频路径

    Returns:
        MessageSegment: 视频 Seg
    """
    seg: MessageSegment
    # 检测文件大小
    file_size_bytes = int(video_path.stat().st_size)
    if file_size_bytes == 0:
        seg = MessageSegment.text("获取视频失败")
    elif file_size_bytes > VIDEO_MAX_MB * 1024 * 1024:
        # 转为文件 Seg
        seg = get_file_seg(video_path)
    else:
        seg = MessageSegment.video(video_path)
    return seg


def get_file_seg(file_path: Path, display_name: str = "") -> MessageSegment:
    """获取文件 Seg

    Args:
        file_path (Path): 文件路径
        display_name (str, optional): 显示名称. Defaults to file_path.name.

    Returns:
        MessageSegment: 文件 Seg
    """
    return MessageSegment(
        "file",
        data={
            "name": display_name if display_name else file_path.name,
            "file": file_path.resolve().as_uri(),
        },
    )
