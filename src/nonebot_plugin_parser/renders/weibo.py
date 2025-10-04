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
        texts = [result.header]
        if result.repost and result.repost.url:
            texts.append(f"源微博详情: {result.repost.url}")
        if result.url:
            texts.append(f"微博详情: {result.url}" if result.url else "")

        yield UniMessage("\n".join(texts) + UniHelper.img_seg(raw=image_raw))

        async for message in self.render_contents(result):
            yield message
