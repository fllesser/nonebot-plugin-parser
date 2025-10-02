"""渲染器模块 - 负责将解析结果渲染为消息"""

from nonebot.internal.matcher import current_bot
from nonebot_plugin_alconna.uniseg import Text, UniMessage

from ..config import NEED_FORWARD
from ..matchers.helper import UniHelper
from ..parsers.data import ParseResult
from .base import BaseRenderer


class Renderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    @staticmethod
    async def render_messages(result: ParseResult) -> list[UniMessage]:
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            list[UniMessage]: 消息列表
        """
        # 构建消息段列表
        messages: list[UniMessage] = []

        texts = (result.header, result.title, result.text, result.extra.get("info"))
        texts = (text for text in texts if text)
        first_message = UniMessage("\n".join(texts))

        if cover_path := result.extra.get("cover_path"):
            first_message += UniHelper.img_seg(cover_path)

        if first_message:
            messages.append(first_message)

        separate_segs, forwardable_segs = result.convert_segs()
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
                # 单条消息
                single_msg = UniMessage()
                for seg in forwardable_segs:
                    single_msg += seg
                messages.append(single_msg)

        # 处理必须单独发送的消息段
        if separate_segs:
            messages.extend(UniMessage(seg) for seg in separate_segs)

        return messages
