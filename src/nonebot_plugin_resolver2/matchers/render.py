"""渲染器模块 - 负责将解析结果渲染为消息"""

from typing import Any

from nonebot import logger
from nonebot_plugin_alconna import UniMessage

from ..config import NICKNAME
from ..parsers.data import AudioContent, ImageContent, ParseResult, VideoContent
from .helper import UniHelper


class Renderer:
    """统一的渲染器，将解析结果转换为消息"""

    @staticmethod
    def render_initial_message(result: ParseResult) -> str:
        """渲染初始提示消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            str: 初始提示消息
        """
        initial_msg = f"{NICKNAME}解析 | {result.platform}"
        if result.title:
            initial_msg += f" - {result.title}"
        if result.author:
            initial_msg += f" - {result.author}"
        return initial_msg

    @staticmethod
    def render_content_messages(result: ParseResult) -> list[UniMessage]:
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            list[UniMessage]: 消息列表
        """
        messages: list[UniMessage] = []

        # 构建消息段列表
        segs: list[Any] = []

        # 添加额外信息（如果有）
        if result.extra_info:
            segs.append(result.extra_info)

        # 添加封面（如果有）
        if result.cover_path:
            segs.append(UniHelper.img_seg(result.cover_path))

        # 根据内容类型处理
        if result.content is None:
            logger.warning(f"解析结果没有内容: {result}")
            return messages

        if isinstance(result.content, VideoContent):
            # 视频内容
            if result.content.video_path:
                # 如果有其他段（封面、额外信息），先发送
                if segs:
                    messages.append(UniMessage(segs))
                # 发送视频
                messages.append(UniMessage([UniHelper.video_seg(result.content.video_path)]))

        elif isinstance(result.content, ImageContent):
            # 图片内容
            for pic_path in result.content.pic_paths:
                segs.append(UniHelper.img_seg(pic_path))
            for dynamic_path in result.content.dynamic_paths:
                segs.append(UniHelper.video_seg(dynamic_path))

            if segs:
                messages.append(UniMessage(segs))

        elif isinstance(result.content, AudioContent):
            # 音频内容
            if result.content.audio_path:
                # 如果有其他段，先发送
                if segs:
                    messages.append(UniMessage(segs))
                # 发送音频
                messages.append(UniMessage([UniHelper.record_seg(result.content.audio_path)]))

        return messages
