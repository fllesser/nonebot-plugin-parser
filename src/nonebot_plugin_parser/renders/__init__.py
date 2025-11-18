import importlib

from ..config import RenderType, pconfig
from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

_CommonRenderer = CommonRenderer()
_DefaultRenderer = DefaultRenderer()

match pconfig.render_type:
    case RenderType.common:
        RENDERER = _CommonRenderer
    case RenderType.default:
        RENDERER = _DefaultRenderer
    case RenderType.htmlkit:
        RENDERER = None


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    try:
        module = importlib.import_module("." + platform, package=__name__)
        renderer_class = getattr(module, "Renderer")
        return renderer_class()
    except (ImportError, AttributeError):
        # fallback to default renderer
        return _CommonRenderer


from nonebot import get_driver


@get_driver().on_startup
async def load_resources():
    CommonRenderer.load_resources()
