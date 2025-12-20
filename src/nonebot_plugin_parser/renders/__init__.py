import importlib.util

from nonebot import get_driver

from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

if importlib.util.find_spec("nonebot_plugin_htmlrender") is None:
    _HTML_RENDERER_AVAILABLE = False
else:
    _HTML_RENDERER_AVAILABLE = True

if importlib.util.find_spec("nonebot_plugin_htmlkit") is None:
    _HTMLKIT_AVAILABLE = False
else:
    _HTMLKIT_AVAILABLE = True


from ..config import pconfig
from ..constants import RenderType

_COMMON_RENDERER = CommonRenderer()
_DEFAULT_RENDERER = DefaultRenderer()
RENDERER = None

match pconfig.render_type:
    case RenderType.common:
        RENDERER = _COMMON_RENDERER
    case RenderType.default:
        RENDERER = _DEFAULT_RENDERER
    case RenderType.htmlrender if _HTML_RENDERER_AVAILABLE:
        from .htmlrender import HtmlRenderer

        RENDERER = HtmlRenderer()
    case RenderType.htmlkit:
        RENDERER = None


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    if not _HTMLKIT_AVAILABLE:
        return _COMMON_RENDERER
    else:
        module = importlib.import_module("." + platform, package=__name__)
        renderer_class: type[BaseRenderer] = getattr(module, "Renderer")
        return renderer_class()


@get_driver().on_startup
async def load_resources():
    CommonRenderer.load_resources()
