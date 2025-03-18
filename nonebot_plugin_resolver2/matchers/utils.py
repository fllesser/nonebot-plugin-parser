from pathlib import Path

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.matcher import Matcher

from nonebot_plugin_resolver2.config import NEED_FORWARD, NICKNAME
from nonebot_plugin_resolver2.constant import VIDEO_MAX_MB
from nonebot_plugin_resolver2.download import download_video


def construct_nodes(segments: MessageSegment | list[MessageSegment | Message | str]) -> Message:
    bot = next(iter(bot for bot in get_bots().values() if isinstance(bot, Bot)))
    user_id = int(bot.self_id)

    def node(content):
        return MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME, content=content)

    segments = segments if isinstance(segments, list) else [segments]
    return Message([node(seg) for seg in segments])


async def send_segments(matcher: type[Matcher], segments: list) -> None:
    if NEED_FORWARD or len(segments) > 4:
        await matcher.send(construct_nodes(segments))
    else:
        for seg in segments:
            await matcher.send(seg)


async def get_video_seg(
    video_path: Path | None = None, url: str | None = None, proxy: str | None = None
) -> MessageSegment:
    seg: MessageSegment | None = None
    try:
        # 如果data以"http"开头，先下载视频
        if not video_path:
            if url and url.startswith("http"):
                video_path = await download_video(url, proxy=proxy)
        assert video_path, "视频路径为空"
        # 检测文件大小
        file_size_bytes = int(video_path.stat().st_size)
        if file_size_bytes == 0:
            seg = MessageSegment.text("获取视频失败")
        elif file_size_bytes > VIDEO_MAX_MB * 1024 * 1024:
            # 转为文件 Seg
            seg = get_file_seg(video_path)
        else:
            seg = MessageSegment.video(video_path)
    except Exception as e:
        seg = MessageSegment.text(f"视频获取失败\n{e}")

    return seg


def get_file_seg(file_path: Path, name: str = "") -> MessageSegment:
    return MessageSegment(
        "file",
        data={
            "name": name if name else file_path.name,
            "file": file_path.resolve().as_uri(),
        },
    )
