import importlib

from .base import BaseRenderer
from .default import Renderer as DefaultRenderer


def get_renderer(platform: str) -> BaseRenderer:
    """根据平台名称获取对应的 Renderer 类"""
    try:
        module = importlib.import_module(f".{platform.lower()}", "nonebot_plugin_resolver2.renders")
        renderer_class = getattr(module, "Renderer")
        if issubclass(renderer_class, BaseRenderer):
            return renderer_class()
    except (ImportError, AttributeError):
        # 如果没有对应的 Renderer 模块或类，返回默认的 Renderer
        pass

    return DefaultRenderer()
