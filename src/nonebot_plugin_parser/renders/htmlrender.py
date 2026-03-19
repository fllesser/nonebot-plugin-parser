import random
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
        # await self.result.ensure_downloads_complete(img_only=True)

        logo = resources.RESOURCES_DIR / f"{self.result.platform.name}.png"
        logo = logo.as_uri() if logo.exists() else None

        font = pconfig.custom_font or resources.DEFAULT_FONT_PATH
        font = font.as_uri() if font.exists() else None

        fallback_pics = list(resources.FAILED_PIC_DIR.glob("*.jpg"))
        fallback_pic = random.choice(fallback_pics).as_uri() if fallback_pics else None

        return await template_to_pic(
            template_path=str(self.templates_dir),
            template_name="card.html.jinja2",
            templates={
                "logo": logo,
                "font": font,
                "result": self.result,
                "fallback_pic": fallback_pic,
                "font_weight": pconfig.custom_font_weight,
                "play_button": resources.DEFAULT_VIDEO_BUTTON_PATH.as_uri(),
                "default_avatar": resources.DEFAULT_AVATAR_PATH.as_uri(),
            },
            pages={"viewport": {"width": 800, "height": 100}},
        )
