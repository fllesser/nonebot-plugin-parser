from typing_extensions import override

from nonebot_plugin_htmlkit import template_to_pic

from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class Renderer(BaseRenderer):
    @override
    async def render_messages(self, result: ParseResult):
        # 生成图片消息
        image_raw = await template_to_pic(
            self.templates_dir.as_posix(),
            "weibo.html.jinja",
            templates={"result": result},
        )
        # 组合文本消息
        texts = [
            result.header,
            f"源微博: {result.repost.url}" if result.repost and result.repost.url else "",
            f"微博详情: {result.url}" if result.url else "",
        ]
        texts = [text for text in texts if text]
        texts[:-1] = [seg + "\n" for seg in texts[:-1]]

        yield UniMessage([texts[0], UniHelper.img_seg(raw=image_raw), *texts[1:]])

        async for message in self.render_contents(result):
            yield message
