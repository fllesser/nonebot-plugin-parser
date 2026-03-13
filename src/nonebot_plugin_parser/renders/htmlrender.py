from __future__ import annotations

from typing_extensions import override

from nonebot import require

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import template_to_pic

from . import resources
from .base import ParseResult, ImageRenderer, pconfig


class HtmlRenderer(ImageRenderer):
    """HTML 渲染器"""

    @override
    async def render_image(self, result: ParseResult) -> bytes:
        # await self._resolve_parse_result(result)
        await result.ensure_img_ready()

        logo = resources.RESOURCES_DIR / f"{result.platform.name}.png"
        logo = logo.as_uri() if logo.exists() else None
        font = pconfig.custom_font or resources.DEFAULT_FONT_PATH
        font = font.as_uri() if font.exists() else None
        play_button = resources.DEFAULT_VIDEO_BUTTON_PATH.as_uri()

        # 动态视频标记：将首张图片提升为视频封面（播放按钮 + 时长）
        # is_video = result.extra.get("is_video", False)
        # if is_video and img_contents and not video_contents:
        #     promoted = img_contents.pop(0)
        #     duration_secs = result.extra.get("duration", 0)
        #     duration_str = None
        #     if duration_secs:
        #         duration_str = f"时长: {fmt_duration(duration_secs)}"
        #     video_contents.append(
        #         CardVideoContent(
        #             cover_path=promoted.path,
        #             duration=duration_str,
        #         )
        #     )
        #     cover_path = promoted.path

        return await template_to_pic(
            template_path=str(self.templates_dir),
            template_name="card.html.jinja",
            templates={
                "result": result,
                "logo": logo,
                "font": font,
                "play_button": play_button,
            },
            pages={
                "viewport": {"width": 800, "height": 100},
                "base_url": f"file://{self.templates_dir}",
            },
        )
