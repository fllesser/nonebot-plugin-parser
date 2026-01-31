from typing import Any, Literal
from pathlib import Path
from functools import wraps
from collections.abc import Callable, Sequence, Awaitable

from nonebot import logger
from nonebot.matcher import current_bot, current_event
from nonebot.adapters import Event
from nonebot_plugin_alconna import SupportAdapter, uniseg
from nonebot_plugin_alconna.uniseg import (
    File,
    Text,
    Image,
    Video,
    Voice,
    Segment,
    Reference,
    CustomNode,
    UniMessage,
)

from .config import pconfig

# from .exception import TipException

ForwardNodeInner = str | Segment | UniMessage
"""转发消息节点内部允许的类型"""

EMOJI_MAP = {
    "fail": ("10060", "❌"),
    "resolving": ("424", "👀"),
    "done": ("144", "🎉"),
}


class UniHelper:
    @staticmethod
    def construct_forward_message(
        segments: Sequence[ForwardNodeInner],
        user_id: str | None = None,
    ) -> Reference:
        """构造转发消息"""
        if user_id is None:
            user_id = current_bot.get().self_id

        nodes: list[CustomNode] = []
        for seg in segments:
            if isinstance(seg, str):
                content = UniMessage([Text(seg)])
            elif isinstance(seg, Segment):
                content = UniMessage([seg])
            else:
                content = seg
            node = CustomNode(uid=user_id, name=pconfig.nickname, content=content)
            nodes.append(node)

        return Reference(nodes=nodes)

    @staticmethod
    def img_seg(
        file: Path | bytes,
    ) -> Image:
        """图片 Seg"""
        if isinstance(file, bytes):
            return Image(raw=file)

        if pconfig.use_base64:
            return Image(raw=file.read_bytes())
        else:
            return Image(path=file)

    @staticmethod
    def record_seg(audio_path: Path) -> Voice:
        """语音 Seg"""
        if pconfig.use_base64:
            return Voice(raw=audio_path.read_bytes())
        else:
            return Voice(path=audio_path)

    @classmethod
    def video_seg(cls, video_path: Path) -> Video | File | Text:
        """视频 Seg"""
        # 检测文件大小
        file_size_byte_count = int(video_path.stat().st_size)
        if file_size_byte_count == 0:
            return Text("视频为空文件")
        elif file_size_byte_count > 100 * 1024 * 1024:
            # 转为文件 Seg
            return cls.file_seg(video_path, display_name=video_path.name)
        else:
            if pconfig.use_base64:
                return Video(raw=video_path.read_bytes())
            else:
                return Video(path=video_path)

    @staticmethod
    def file_seg(
        file: Path,
        display_name: str | None = None,
    ) -> File:
        """文件 Seg"""
        if not display_name:
            display_name = file.name
        if not display_name:
            raise ValueError("文件名不能为空")
        if pconfig.use_base64:
            return File(raw=file.read_bytes(), name=display_name)
        else:
            return File(path=file, name=display_name)

    @classmethod
    async def message_reaction(
        cls,
        event: Event,
        status: Literal["fail", "resolving", "done"],
    ) -> None:
        """发送消息回应"""
        message_id = uniseg.get_message_id(event)
        target = uniseg.get_target(event)

        if target.adapter in (SupportAdapter.onebot11, SupportAdapter.qq):
            emoji = EMOJI_MAP[status][0]
        else:
            emoji = EMOJI_MAP[status][1]

        try:
            await uniseg.message_reaction(emoji, message_id=message_id)
        except Exception:
            logger.warning(f"reaction {emoji} to {message_id} failed, maybe not support")

    @classmethod
    def with_reaction(cls, func: Callable[..., Awaitable[Any]]):
        """自动回应装饰器"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            event = current_event.get()
            await cls.message_reaction(event, "resolving")

            try:
                result = await func(*args, **kwargs)
            # except TipException as e:
            #     await UniMessage.text(e.message).send()
            #     raise
            except Exception:
                await cls.message_reaction(event, "fail")
                raise

            await cls.message_reaction(event, "done")
            return result

        return wrapper
