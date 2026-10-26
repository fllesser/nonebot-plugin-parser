import importlib

from nonebot import logger

from .base import BaseRenderer
from .common import CommonRenderer
from .default import DefaultRenderer

RENDERER: type[BaseRenderer] | None = None

from ..utils import is_module_available
from ..config import pconfig
from ..constants import RenderType

match pconfig.render_type:
    case RenderType.common:
        RENDERER = CommonRenderer
    case RenderType.default:
        RENDERER = DefaultRenderer
    case RenderType.takumi | RenderType.htmlrender:
        if is_module_available("takumi_py"):
            from .htmlrender import HtmlRenderer

            RENDERER = HtmlRenderer
        else:
            logger.warning("未安装 `takumi-py`, 已回退到 common 渲染器")
            RENDERER = CommonRenderer


def get_renderer(platform: str) -> type[BaseRenderer]:
    """根据平台名称获取对应的 Renderer 类"""
    if RENDERER:
        return RENDERER

    module = importlib.import_module("." + platform, package=__name__)
    return getattr(module, "Renderer")
