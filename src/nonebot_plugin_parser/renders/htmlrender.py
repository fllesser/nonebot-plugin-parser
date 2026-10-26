import asyncio
from pathlib import Path
from typing_extensions import override

from jinja2 import Environment, FileSystemLoader, select_autoescape
from takumi_py import Renderer, FontResource, ImageResource

from . import resources
from .base import ImageRenderer, pconfig
from ..parsers.task import PathTask

_STYLESHEET_START = "/* TAKUMI_STYLESHEET_START */"
_STYLESHEET_END = "/* TAKUMI_STYLESHEET_END */"


def _extract_stylesheet(html: str) -> tuple[str, str]:
    before, start_marker, remainder = html.partition(_STYLESHEET_START)
    if not start_marker:
        raise ValueError("card.html.jinja2 is missing the stylesheet start marker")

    stylesheet, end_marker, after = remainder.partition(_STYLESHEET_END)
    if not end_marker:
        raise ValueError("card.html.jinja2 is missing the stylesheet end marker")

    return before + after, stylesheet


async def _path_task_uri(path_task: PathTask | None) -> str | None:
    if path_task is None:
        return None

    path = await path_task.safe_get()
    return path.as_uri() if path else None


class HtmlRenderer(ImageRenderer):
    """HTML 渲染器"""

    @override
    async def render_image(self) -> bytes:
        logo_path = resources.RESOURCES_DIR / f"{self.result.platform.name}.png"
        font_path = pconfig.custom_font or resources.DEFAULT_FONT_PATH
        fallback_path = resources.random_fallback_pic()

        image_paths = [
            fallback_path,
            resources.DEFAULT_VIDEO_BUTTON_PATH,
            resources.DEFAULT_AVATAR_PATH,
        ]
        if logo_path.is_file():
            image_paths.append(logo_path)

        download_results = await asyncio.gather(
            *self.result._iterate_download_coros(img_only=True), return_exceptions=True
        )
        image_paths.extend(path for path in download_results if isinstance(path, Path))
        images = [ImageResource(path.as_uri(), path.read_bytes()) for path in dict.fromkeys(image_paths)]

        configured_renderer = Renderer(load_default_fonts=False)
        font_families = configured_renderer.register_font(FontResource(font_path.read_bytes()))

        # Render the Jinja template asynchronously because PathTask.uri is async.
        environment = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(
                enabled_extensions=("html", "xml", "jinja"),
                default_for_string=False,
            ),
            enable_async=True,
        )
        environment.filters["path_uri"] = _path_task_uri
        template_context: dict[str, object] = {
            "logo": logo_path.as_uri() if logo_path.is_file() else None,
            "font": font_path.as_uri() if font_path.is_file() else None,
            "result": self.result,
            "font_weight": pconfig.custom_font_weight,
            "fallback_pic": fallback_path.as_uri(),
            "play_button": resources.DEFAULT_VIDEO_BUTTON_PATH.as_uri(),
            "default_avatar": resources.DEFAULT_AVATAR_PATH.as_uri(),
        }
        html = await environment.get_template("card.html.jinja2").render_async(**template_context)
        html, stylesheet = _extract_stylesheet(html)

        # Takumi's synchronous native rendering runs outside the event loop.
        return await asyncio.to_thread(
            configured_renderer.render_html,
            html,
            stylesheets=[stylesheet],
            font_families=font_families,
            images=images,
            width=800,
            height=None,
        )
