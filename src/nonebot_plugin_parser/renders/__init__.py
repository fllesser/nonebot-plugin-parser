import importlib

from nonebot import get_driver

from .. import utils
from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

_HTML_RENDER_AVAILABLE = utils.is_module_available("nonebot_plugin_htmlrender")
_HTMLKIT_AVAILABLE = utils.is_module_available("nonebot_plugin_htmlkit")

from ..config import pconfig
from ..constants import RenderType

match pconfig.render_type:
    case RenderType.common:
        RENDERER = CommonRenderer
    case RenderType.default:
        RENDERER = DefaultRenderer
    case RenderType.htmlrender if _HTML_RENDER_AVAILABLE:
        from .htmlrender import HtmlRenderer

        RENDERER = HtmlRenderer
    case RenderType.htmlkit:
        RENDERER = None


def get_renderer(platform: str) -> type[BaseRenderer]:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    if not _HTMLKIT_AVAILABLE:
        return CommonRenderer
    else:
        module = importlib.import_module("." + platform, package=__name__)
        return getattr(module, "Renderer")


@get_driver().on_startup
async def load_resources():
    CommonRenderer.load_resources()
