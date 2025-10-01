"""渲染器模块 - 负责将解析结果渲染为消息"""

from typing import Any

from nonebot import logger
from nonebot.internal.matcher import current_bot
from nonebot_plugin_alconna import Image, UniMessage
from nonebot_plugin_alconna.uniseg import Text

from ..config import NEED_FORWARD
from ..parsers.data import AudioContent, ImageContent, ParseResult, VideoContent
from .helper import UniHelper


class Renderer:
    """统一的渲染器，将解析结果转换为消息"""

    @staticmethod
    def render_messages(result: ParseResult) -> list[UniMessage]:
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            list[UniMessage]: 消息列表
        """
        # 构建消息段列表
        segs: list[Any] = []

        # 添加标题
        segs.append(f"标题: {result.title}")

        # 添加额外信息（如果有）
        if result.extra_info:
            segs.append(result.extra_info)

        # 添加封面（如果有）
        if result.cover_path:
            segs.append(UniHelper.img_seg(result.cover_path))

        # 根据内容类型处理
        if result.content is None:
            logger.warning(f"解析结果没有内容: {result}")
            return []

        if isinstance(result.content, VideoContent):
            # 视频内容
            if result.content.video_path:
                segs.append(UniHelper.video_seg(result.content.video_path))

        elif isinstance(result.content, ImageContent):
            # 图片内容
            for pic_path in result.content.pic_paths:
                segs.append(UniHelper.img_seg(pic_path))
            for dynamic_path in result.content.dynamic_paths:
                segs.append(UniHelper.video_seg(dynamic_path))

        elif isinstance(result.content, AudioContent):
            # 音频内容
            if result.content.audio_path:
                segs.append(UniHelper.record_seg(result.content.audio_path))

        if not segs:
            return []

        # 分离可以合并转发的消息段(文本和图片)和必须单独发送的消息段(视频、语音、文件)
        separate_segs = []  # 必须单独发送的消息段(视频、语音、文件)
        forwardable_segs = []  # 可以合并转发的消息段(文本和图片)

        for seg in segs:
            # 文本和图片可以合并转发,其他类型(视频、语音、文件)需要单独发送
            if isinstance(seg, str) or isinstance(seg, Image):
                forwardable_segs.append(seg)
            else:
                separate_segs.append(seg)

        messages: list[UniMessage] = []

        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
            if NEED_FORWARD or len(forwardable_segs) > 4:
                # 使用转发消息
                bot = current_bot.get()
                forward_msg = UniHelper.construct_forward_message(bot.self_id, forwardable_segs)
                messages.append(UniMessage([forward_msg]))
            else:
                # 直接发送
                forwardable_segs[:-1] = [
                    Text(seg + "\n") if isinstance(seg, str) else seg for seg in forwardable_segs[:-1]
                ]
                messages.append(UniMessage(forwardable_segs))

        # 处理必须单独发送的消息段
        messages.append(UniMessage(separate_segs))

        return messages
