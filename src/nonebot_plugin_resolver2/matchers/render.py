"""渲染器模块 - 负责将解析结果渲染为消息"""

from typing import Any

from nonebot import logger
from nonebot.internal.matcher import current_bot
from nonebot_plugin_alconna import UniMessage

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

        # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
        if not segs:
            return []

        if NEED_FORWARD or len(segs) > 4:
            # 使用转发消息
            bot = current_bot.get()
            forward_msg = UniHelper.construct_forward_message(bot.self_id, segs)
            return [UniMessage([forward_msg])]
        else:
            # 直接发送所有消息段
            return [UniMessage(segs)]
