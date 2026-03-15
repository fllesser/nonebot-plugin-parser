from typing_extensions import override

from nonebot import require

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import template_to_pic

from . import resources
from .base import ImageRenderer, pconfig


class HtmlRenderer(ImageRenderer):
    """HTML 渲染器"""

    @override
    async def render_image(self) -> bytes:
        await self.result.ensure_downloads_complete(img_only=True)

        logo = resources.RESOURCES_DIR / f"{self.result.platform.name}.png"
        logo = logo.as_uri() if logo.exists() else None
        font = pconfig.custom_font or resources.DEFAULT_FONT_PATH
        font = font.as_uri() if font.exists() else None
        play_button = resources.DEFAULT_VIDEO_BUTTON_PATH.as_uri()

        return await template_to_pic(
            template_path=str(self.templates_dir),
            template_name="card.html.jinja",
            templates={
                "result": self.result,
                "logo": logo,
                "font": font,
                "play_button": play_button,
            },
            pages={"viewport": {"width": 800, "height": 100}},
        )
