"""渲染器模块 - 负责将解析结果渲染为消息"""

from typing_extensions import override

from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class Renderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    @override
    async def render_messages(self, result: ParseResult):
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            Generator[UniMessage[Any], None, None]: 消息生成器
        """

        texts = (result.header, result.text, result.extra.get("info"), result.url)
        texts = (text for text in texts if text)
        first_message = UniMessage("\n".join(texts))

        if result.cover_path:
            first_message += UniHelper.img_seg(result.cover_path)

        yield first_message

        separate_segs, forwardable_segs = await result.convert_segs()

        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
            forward_msg = UniHelper.construct_forward_message(forwardable_segs)
            yield UniMessage(forward_msg)

        # 处理必须单独发送的消息段
        if separate_segs:
            for seg in separate_segs:
                yield UniMessage(seg)
