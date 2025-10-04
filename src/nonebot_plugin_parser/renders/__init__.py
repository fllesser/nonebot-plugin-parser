import importlib

from ..config import RenderType, rconfig
from .base import BaseRenderer
from .common import Renderer as CommonRenderer
from .default import Renderer as DefaultRenderer


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    match rconfig.r_render_type:
        case RenderType.common:
            return CommonRenderer()
        case RenderType.default:
            return DefaultRenderer()
    # htmlkit renderer
    try:
        module = importlib.import_module("." + platform, package=__name__)
        renderer_class = getattr(module, "Renderer")
        if issubclass(renderer_class, BaseRenderer):
            return renderer_class()
    except (ImportError, AttributeError):
        # 如果没有对应的 Renderer 模块或类，返回默认的 Renderer
        pass
    # fallback to default renderer
    return DefaultRenderer()
