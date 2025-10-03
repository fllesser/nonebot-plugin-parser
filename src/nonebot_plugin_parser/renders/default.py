"""渲染器模块 - 负责将解析结果渲染为消息"""

from typing_extensions import override

from ..helper import UniHelper, UniMessage
from ..parsers import ParseResult
from .base import BaseRenderer


class Renderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    @override
    async def render_messages(self, result: ParseResult):
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            list[UniMessage]: 消息列表
        """
        # 构建消息段列表
        messages: list[UniMessage] = []

        texts = (result.header, result.text, result.extra.get("info"), result.url)
        texts = (text for text in texts if text)
        first_message = UniMessage("\n".join(texts))

        if result.cover_path:
            first_message += UniHelper.img_seg(result.cover_path)

        separate_segs, forwardable_segs = result.convert_segs()

        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
            if self.need_forward or len(forwardable_segs) > 2:
                forward_msg = UniHelper.construct_forward_message(forwardable_segs)
                messages.append(UniMessage([forward_msg]))
            else:
                forwardable_segs[:-1] = [seg + "\n" for seg in forwardable_segs[:-1]]
                # 单条消息
                for seg in forwardable_segs:
                    first_message += seg

        messages.insert(0, first_message)
        # 处理必须单独发送的消息段
        if separate_segs:
            messages.extend(UniMessage(seg) for seg in separate_segs)

        return messages
