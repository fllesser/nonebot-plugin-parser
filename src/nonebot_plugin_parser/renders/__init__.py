import importlib

from nonebot import logger, get_driver

from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer


def is_module_available(module_name: str) -> bool:
    """检查模块是否可用"""
    import importlib.util

    return importlib.util.find_spec(module_name) is not None


from ..config import pconfig
from ..constants import RenderType

RENDERER: type[BaseRenderer] | None = None

match pconfig.render_type:
    case RenderType.common:
        RENDERER = CommonRenderer
    case RenderType.default:
        RENDERER = DefaultRenderer
    case RenderType.htmlrender:
        if is_module_available("nonebot_plugin_htmlrender"):
            from .htmlrender import HtmlRenderer

            RENDERER = HtmlRenderer
        else:
            logger.warning("未安装 `nonebot_plugin_htmlrender`, 已回退到 common 渲染器")
            RENDERER = CommonRenderer
    case RenderType.htmlkit:
        if is_module_available("nonebot_plugin_htmlkit"):
            from .htmlkit import HtmlKitRenderer

            RENDERER = HtmlKitRenderer
        else:
            logger.warning("未安装 `nonebot_plugin_htmlkit`, 已回退到 common 渲染器")
            RENDERER = CommonRenderer


def get_renderer(platform: str) -> type[BaseRenderer]:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    module = importlib.import_module("." + platform, package=__name__)
    return getattr(module, "Renderer")


@get_driver().on_startup
async def load_resources():
    CommonRenderer.load_resources()
