from __future__ import annotations

from PIL import Image
from nonebot import logger, get_driver
from apilmoji import EmojiCDNSource

from .. import resources
from ...config import pconfig
from .typography import CardFonts, CardTheme

PILImage = Image.Image

# apilmoji emoji 源
EMOJI_SOURCE = EmojiCDNSource(
    base_url=pconfig.emoji_cdn,
    style=pconfig.emoji_style,
    cache_dir=pconfig.cache_dir / "emojis",
    show_progress=True,
)

DEFAULT_THEME = CardTheme(
    name=(0, 122, 255),
    title=(102, 51, 153),
    body=(51, 51, 51),
    muted=(136, 136, 136),
)

AVATAR_SIZE = 80
FONTS: CardFonts
PLATFORM_LOGOS: dict[str, PILImage]
AVATAR_IMAGE: PILImage
VIDEO_BUTTON_IMAGE: PILImage

_resources_loaded = False


@get_driver().on_startup
async def load_common_renderer_resources():
    load_resources()


def ensure_resources() -> None:
    if _resources_loaded:
        return
    load_resources()


def load_resources() -> None:
    """加载渲染资源（幂等）"""
    global _resources_loaded, FONTS, PLATFORM_LOGOS, AVATAR_IMAGE, VIDEO_BUTTON_IMAGE

    if _resources_loaded:
        return

    FONTS = _load_fonts()
    PLATFORM_LOGOS = _load_platform_logos()
    AVATAR_IMAGE = _load_default_avatar()
    VIDEO_BUTTON_IMAGE = _load_video_button()

    _resources_loaded = True


def _load_fonts() -> CardFonts:
    """字体（昵称 / 标题 / 正文 / 辅助文案）"""
    font_path = pconfig.custom_font or resources.DEFAULT_FONT_PATH
    loaded = CardFonts.load(font_path, DEFAULT_THEME)
    logger.success(f"加载字体「{font_path.name}」成功")
    return loaded


def _load_platform_logos() -> dict[str, PILImage]:
    """平台 Logo"""
    from ...constants import PlatformEnum

    logos: dict[str, PILImage] = {}
    loaded_platforms = []
    for platform_name in PlatformEnum:
        logo_path = resources.RESOURCES_DIR / f"{platform_name}.png"
        if logo_path.exists():
            with Image.open(logo_path) as img:
                logos[str(platform_name)] = img.convert("RGBA")
                loaded_platforms.append(platform_name)
    logger.debug(f"加载 Logo「{', '.join(loaded_platforms)}」成功")
    return logos


def _load_default_avatar() -> PILImage:
    """默认头像（作者无头像或加载失败时回退）"""
    with Image.open(resources.DEFAULT_AVATAR_PATH) as img:
        loaded = img.convert("RGBA").resize((AVATAR_SIZE, AVATAR_SIZE))
    logger.debug(f"加载头像「{resources.DEFAULT_AVATAR_PATH.name}」成功")
    return loaded


def _load_video_button() -> PILImage:
    """视频播放按钮（封面居中叠加，半透明）"""
    with Image.open(resources.DEFAULT_VIDEO_BUTTON_PATH) as img:
        button = img.convert("RGBA").resize((100, 100))
    alpha = button.split()[-1]
    alpha = alpha.point(lambda x: int(x * 0.6))
    button.putalpha(alpha)
    logger.debug(f"加载视频播放按钮「{resources.DEFAULT_VIDEO_BUTTON_PATH.name}」成功")
    return button
