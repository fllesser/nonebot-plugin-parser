from typing_extensions import override

from nonebot import require

require("nonebot_plugin_htmlkit")
from nonebot_plugin_htmlkit import template_to_pic

from .base import ParseResult, ImageRenderer


class Renderer(ImageRenderer):
    @override
    async def render_image(self, result: ParseResult) -> bytes:
        return await template_to_pic(
            self.templates_dir.as_posix(),
            "weibo.html.jinja",
            templates={"result": result},
        )
