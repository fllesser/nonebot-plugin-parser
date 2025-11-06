import importlib

from ..config import RenderType, pconfig
from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

match pconfig.render_type:
    case RenderType.common:
        RENDERER = CommonRenderer
    case RenderType.default:
        RENDERER = DefaultRenderer
    case RenderType.htmlkit:
        RENDERER = None


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER()

    try:
        module = importlib.import_module("." + platform, package=__name__)
        renderer_class = getattr(module, "Renderer")
        if issubclass(renderer_class, BaseRenderer):
            return renderer_class()
    except (ImportError, AttributeError):
        # 如果没有对应的 Renderer 模块或类，返回默认的 Renderer
        pass
    # fallback to default renderer
    return CommonRenderer()


from nonebot import get_driver


@get_driver().on_startup
async def load_resources():
    CommonRenderer.load_resources()
