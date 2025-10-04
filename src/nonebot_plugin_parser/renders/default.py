"""渲染器模块 - 负责将解析结果渲染为消息"""

from typing_extensions import override

from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class DefaultRenderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    @override
    async def render_messages(self, result: ParseResult):
        """渲染内容消息

        Args:
            result (ParseResult): 解析结果

        Returns:
            Generator[UniMessage[Any], None, None]: 消息生成器
        """

        texts: list[str] = [result.header, result.text, result.extra_info, result.display_url]
        texts = [text for text in texts if text]
        texts[:-1] = [seg + "\n" for seg in texts[:-1]]

        if result.cover_path:
            segs = [texts[0], UniHelper.img_seg(result.cover_path), *texts[1:]]
        else:
            segs = texts
        yield UniMessage(segs)

        async for message in self.render_contents(result):
            yield message
