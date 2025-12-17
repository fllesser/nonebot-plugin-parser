import importlib.util

from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

_COMMON_RENDERER = CommonRenderer()
_DEFAULT_RENDERER = DefaultRenderer()

if importlib.util.find_spec("nonebot_plugin_htmlrender") is None:
    _HTML_RENDERER = None
else:
    from .htmlrender import HtmlRenderer

    _HTML_RENDERER = HtmlRenderer()

from ..config import pconfig
from ..constants import RenderType

match pconfig.render_type:
    case RenderType.common:
        RENDERER = _COMMON_RENDERER
    case RenderType.default:
        RENDERER = _DEFAULT_RENDERER
    case RenderType.htmlrender:
        RENDERER = _COMMON_RENDERER if _HTML_RENDERER is None else _HTML_RENDERER
    case RenderType.htmlkit:
        RENDERER = None


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    if importlib.util.find_spec("nonebot_plugin_htmlkit") is None:
        # fallback to default renderer
        return _COMMON_RENDERER
    else:
        module = importlib.import_module("." + platform, package=__name__)
        renderer_class = getattr(module, "Renderer")
        return renderer_class()


from nonebot import get_driver


@get_driver().on_startup
async def load_resources():
    CommonRenderer.load_resources()
