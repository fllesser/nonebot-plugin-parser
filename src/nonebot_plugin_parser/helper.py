from collections.abc import Sequence
from pathlib import Path

from nonebot.internal.matcher import current_bot
from nonebot_plugin_alconna import File, Image, Text, Video
from nonebot_plugin_alconna.uniseg import Segment, UniMessage, Voice
from nonebot_plugin_alconna.uniseg.segment import CustomNode, Reference

from .config import pconfig
from .exception import ParseException


class UniHelper:
    @staticmethod
    def construct_forward_message(
        segments: Sequence[str | Segment | UniMessage], user_id: str | None = None
    ) -> Reference:
        """构造转发消息

        Args:
            user_id (str): 用户ID
            segments (Sequence[Segment | str]): 消息段

        Returns:
            Reference: 转发消息
        """
        if user_id is None:
            user_id = current_bot.get().self_id
        nodes = []
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

    @classmethod
    async def send_segments(cls, segments: Sequence[Segment | str]) -> None:
        """发送消息段

        Args:
            segments (Sequence[Segment | str]): 消息段
        """

        if len(segments) > 2:
            forward_msg = cls.construct_forward_message(segments)
            await UniMessage([forward_msg]).send()

        else:
            segments = list(segments)
            segments[:-1] = [Text(seg + "\n") if isinstance(seg, str) else seg for seg in segments[:-1]]
            await UniMessage(segments).send()

    @staticmethod
    def img_seg(img_path: Path | None = None, raw: bytes | None = None) -> Image:
        """获取图片 Seg

        Args:
            img_path (Path): 图片路径

        Returns:
            Image: 图片 Seg
        """

        if raw is not None:
            return Image(raw=raw)

        if img_path is None:
            raise ValueError("img_path 和 raw 不能都为 None")

        if pconfig.use_base64:
            return Image(raw=img_path.read_bytes())
        else:
            return Image(path=img_path)

    @staticmethod
    def record_seg(audio_path: Path) -> Voice:
        """获取语音 Seg

        Args:
            audio_path (Path): 语音路径

        Returns:
            Voice: 语音 Seg
        """
        if pconfig.use_base64:
            return Voice(raw=audio_path.read_bytes())
        else:
            return Voice(path=audio_path)

    @classmethod
    def video_seg(cls, video_path: Path) -> Video | File | Text:
        """获取视频 Seg

        Returns:
            Video | File | Text: 视频 Seg
        """
        # 检测文件大小
        file_size_byte_count = int(video_path.stat().st_size)
        if file_size_byte_count == 0:
            raise ParseException("视频文件大小为 0")
        elif file_size_byte_count > 100 * 1024 * 1024:
            # 转为文件 Seg
            return cls.file_seg(video_path, display_name=video_path.name)
        else:
            if pconfig.use_base64:
                return Video(raw=video_path.read_bytes())
            else:
                return Video(path=video_path)

    @staticmethod
    def file_seg(file: Path, display_name: str = "") -> File:
        """获取文件 Seg

        Args:
            file (Path): 文件路径
            display_name (str, optional): 显示名称. Defaults to file.name.

        Returns:
            File: 文件 Seg
        """
        if not display_name:
            display_name = file.name
        if not display_name:
            raise ValueError("文件名不能为空")
        if pconfig.use_base64:
            return File(raw=file.read_bytes(), name=display_name)
        else:
            return File(path=file, name=display_name)
