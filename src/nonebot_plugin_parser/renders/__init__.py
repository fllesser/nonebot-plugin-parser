import importlib

from ..config import RenderType, pconfig
from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

_DEFAULT_RENDERER = DefaultRenderer()
_COMMON_RENDERER = CommonRenderer()

match pconfig.render_type:
    case RenderType.common:
        RENDERER = _COMMON_RENDERER
    case RenderType.default:
        RENDERER = _DEFAULT_RENDERER
    case RenderType.htmlkit:
        RENDERER = None


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    try:
        module = importlib.import_module("." + platform, package=__name__)
        renderer_class = getattr(module, "Renderer")
        if issubclass(renderer_class, BaseRenderer):
            return renderer_class()
    except (ImportError, AttributeError):
        # 如果没有对应的 Renderer 模块或类，返回默认的 Renderer
        pass
    # fallback to default renderer
    return _COMMON_RENDERER


from nonebot import get_driver


@get_driver().on_startup
async def _():
    # CommonRenderer.load_fonts()
    CommonRenderer.load_custom_fonts()
