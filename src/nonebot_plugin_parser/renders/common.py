from io import BytesIO
from typing import ClassVar
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass
from typing_extensions import override

import emoji
from PIL import Image, ImageDraw, ImageFont
from nonebot import logger
from apilmoji import Apilmoji, EmojiCDNSource
from apilmoji.core import get_font_height

from .base import ParseResult, ImageRenderer
from ..config import pconfig
from ..parsers import GraphicsContent

Color = tuple[int, int, int]
PILImage = Image.Image
PILImageDraw = ImageDraw.ImageDraw

try:
    import emosvg
except ImportError:
    emosvg = None


@dataclass(eq=False, frozen=True, slots=True)
class FontInfo:
    """字体信息数据类"""

    font: ImageFont.FreeTypeFont
    fill: Color
    line_height: int
    cjk_width: int

    def __hash__(self) -> int:
        return hash((id(self.font), self.line_height, self.cjk_width, self.fill))

    @lru_cache(maxsize=500)
    def get_char_width(self, char: str) -> int:
        bbox = self.font.getbbox(char)
        return int(bbox[2] - bbox[0])

    def get_char_width_fast(self, char: str) -> int:
        if "\u4e00" <= char <= "\u9fff":
            return self.cjk_width
        return self.get_char_width(char)

    def get_text_width(self, text: str) -> int:
        if not text:
            return 0
        return sum(self.get_char_width_fast(char) for char in text)


@dataclass(eq=False, frozen=True, slots=True)
class FontSet:
    """字体集数据类"""

    _FONT_INFOS = (
        ("name", 28, (0, 122, 255)),
        ("title", 30, (102, 51, 153)),
        ("text", 24, (51, 51, 51)),
        ("extra", 24, (136, 136, 136)),
        ("indicator", 60, (255, 255, 255)),
    )

    name: FontInfo
    title: FontInfo
    text: FontInfo
    extra: FontInfo
    indicator: FontInfo

    @classmethod
    def new(cls, font_path: Path):
        font_infos: dict[str, FontInfo] = {}
        for name, size, fill in cls._FONT_INFOS:
            font = ImageFont.truetype(font_path, size)
            height = get_font_height(font)
            font_infos[name] = FontInfo(font=font, fill=fill, line_height=height, cjk_width=size)
        return FontSet(**font_infos)


@dataclass
class RenderContext:
    """渲染上下文"""

    result: ParseResult
    card_width: int
    content_width: int
    image: PILImage
    draw: PILImageDraw
    not_repost: bool = True
    y_pos: int = 0


class CommonRenderer(ImageRenderer):
    """统一渲染器"""

    # 布局常量
    PADDING = 25
    AVATAR_SIZE = 80
    AVATAR_TEXT_GAP = 15
    SECTION_SPACING = 15
    NAME_TIME_GAP = 5
    DEFAULT_CARD_WIDTH = 800

    # 图片处理
    MAX_COVER_HEIGHT = 800
    MAX_IMAGE_HEIGHT = 800
    IMAGE_2_GRID_SIZE = 400
    IMAGE_3_GRID_SIZE = 300
    IMAGE_GRID_SPACING = 4
    IMAGE_GRID_COLS = 3
    MAX_IMAGES_DISPLAY = 9

    # 转发
    REPOST_PADDING = 12
    REPOST_SCALE = 0.88

    # 颜色
    BG_COLOR: ClassVar[Color] = (255, 255, 255)
    REPOST_BG_COLOR: ClassVar[Color] = (247, 247, 247)
    REPOST_BORDER_COLOR: ClassVar[Color] = (230, 230, 230)

    # 资源路径
    _RESOURCES = "resources"
    _EMOJIS = "emojis"
    RESOURCES_DIR: ClassVar[Path] = Path(__file__).parent / _RESOURCES
    DEFAULT_FONT_PATH: ClassVar[Path] = RESOURCES_DIR / "HYSongYunLangHeiW-1.ttf"
    DEFAULT_VIDEO_BUTTON_PATH: ClassVar[Path] = RESOURCES_DIR / "media_button.png"
    EMOJI_SOURCE: ClassVar[EmojiCDNSource] = EmojiCDNSource(
        base_url=pconfig.emoji_cdn,
        style=pconfig.emoji_style,
        cache_dir=pconfig.cache_dir / _EMOJIS,
        show_progress=True,
    )

    @classmethod
    def load_resources(cls):
        """加载资源"""
        cls._load_fonts()
        cls._load_video_button()
        cls._load_platform_logos()

    @classmethod
    def _load_fonts(cls):
        font_path = pconfig.custom_font or cls.DEFAULT_FONT_PATH
        cls.fontset = FontSet.new(font_path)
        logger.success(f"加载字体「{font_path.name}」成功")

    @classmethod
    def _load_video_button(cls):
        with Image.open(cls.DEFAULT_VIDEO_BUTTON_PATH) as img:
            cls.video_button_image: PILImage = img.convert("RGBA")
        alpha = cls.video_button_image.split()[-1]
        alpha = alpha.point(lambda x: int(x * 0.3))
        cls.video_button_image.putalpha(alpha)

    @classmethod
    def _load_platform_logos(cls):
        from ..constants import PlatformEnum

        cls.platform_logos: dict[str, PILImage] = {}
        for platform_name in PlatformEnum:
            logo_path = cls.RESOURCES_DIR / f"{platform_name}.png"
            if logo_path.exists():
                with Image.open(logo_path) as img:
                    cls.platform_logos[str(platform_name)] = img.convert("RGBA")

    @override
    async def render_image(self, result: ParseResult) -> bytes:
        image = await self._create_card_image(result)
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    async def _create_card_image(self, result: ParseResult, not_repost: bool = True) -> PILImage:
        """单次遍历渲染"""
        card_width = self.DEFAULT_CARD_WIDTH
        content_width = card_width - 2 * self.PADDING

        # 初始估算高度（后续可动态扩展）
        estimated_height = self._estimate_height(result, content_width)
        bg_color = self.BG_COLOR if not_repost else self.REPOST_BG_COLOR
        image = Image.new("RGB", (card_width, estimated_height), bg_color)

        ctx = RenderContext(
            result=result,
            card_width=card_width,
            content_width=content_width,
            image=image,
            draw=ImageDraw.Draw(image),
            not_repost=not_repost,
            y_pos=self.PADDING,
        )

        # 单次遍历渲染各部分
        await self._render_header(ctx)
        await self._render_title(ctx)
        await self._render_cover_or_images(ctx)
        await self._render_text(ctx)
        await self._render_extra(ctx)
        await self._render_repost(ctx)

        # 裁剪到实际高度
        final_height = ctx.y_pos + self.PADDING
        logger.debug(f"估算高度: {estimated_height}, 画布高度: {ctx.image.height}, 最终高度: {final_height}")
        return ctx.image.crop((0, 0, card_width, final_height))

    def _ensure_canvas_height(self, ctx: RenderContext, needed_height: int) -> None:
        """确保画布有足够高度，不够则扩展"""
        if ctx.y_pos + needed_height + self.PADDING > ctx.image.height:
            # 扩展画布（每次扩展 1.6 倍或至少满足需求）
            new_height = max(int(ctx.image.height * 1.6), ctx.y_pos + needed_height + self.PADDING * 2)
            logger.debug(f"扩展画布高度: {ctx.image.height} -> {new_height}")
            bg_color = self.BG_COLOR if ctx.not_repost else self.REPOST_BG_COLOR
            new_image = Image.new("RGB", (ctx.card_width, new_height), bg_color)
            new_image.paste(ctx.image, (0, 0))
            ctx.image = new_image
            ctx.draw = ImageDraw.Draw(new_image)

    def _estimate_height(self, result: ParseResult, content_width: int) -> int:
        """估算画布高度"""
        height = self.PADDING * 2  # 上下边距

        # 头部（头像 + 名称 + 时间）
        if result.author:
            height += self.AVATAR_SIZE + self.SECTION_SPACING

        # 标题（估算，考虑换行符）
        if result.title:
            lines = result.title.count("\n") + 1 + (len(result.title) * self.fontset.title.cjk_width // content_width)
            height += lines * self.fontset.title.line_height + self.SECTION_SPACING

        # 封面或图片
        height += self.MAX_COVER_HEIGHT + self.SECTION_SPACING

        # 图文内容
        if graphics_contents := result.graphics_contents:
            height += len(graphics_contents) * self.MAX_COVER_HEIGHT + self.SECTION_SPACING

        # 正文（估算，考虑换行符）
        if result.text:
            lines = result.text.count("\n") + 1 + (len(result.text) * self.fontset.text.cjk_width // content_width)
            height += lines * self.fontset.text.line_height + self.SECTION_SPACING

        # 额外信息
        if result.extra_info:
            height += self.fontset.extra.line_height * 3 + self.SECTION_SPACING

        # 转发内容（递归估算）
        if result.repost:
            height += int(self._estimate_height(result.repost, content_width) * self.REPOST_SCALE)
            height += self.REPOST_PADDING * 2 + self.SECTION_SPACING

        # 增加安全余量，防止估算不足（最后会裁剪）
        return height

    async def _render_header(self, ctx: RenderContext) -> None:
        """渲染头部（头像 + 名称 + 时间）"""
        if ctx.result.author is None:
            return

        x_pos = self.PADDING

        # 头像
        avatar_path = await ctx.result.author.get_avatar_path()
        avatar = self._load_avatar(avatar_path)
        ctx.image.paste(avatar, (x_pos, ctx.y_pos), avatar)

        # 文字区域
        text_x = self.PADDING + self.AVATAR_SIZE + self.AVATAR_TEXT_GAP
        name_height = self.fontset.name.line_height
        time_str = ctx.result.formartted_datetime
        time_height = (self.NAME_TIME_GAP + self.fontset.extra.line_height) if time_str else 0
        text_height = name_height + time_height

        # 垂直居中
        text_y = ctx.y_pos + (self.AVATAR_SIZE - text_height) // 2

        # 名称
        ctx.draw.text(
            (text_x, text_y),
            ctx.result.author.name,
            font=self.fontset.name.font,
            fill=self.fontset.name.fill,
        )
        text_y += name_height

        # 时间
        if time_str:
            text_y += self.NAME_TIME_GAP
            ctx.draw.text(
                (text_x, text_y),
                time_str,
                font=self.fontset.extra.font,
                fill=self.fontset.extra.fill,
            )

        # 平台 Logo
        if ctx.not_repost:
            platform_name = ctx.result.platform.name
            if platform_name in self.platform_logos:
                logo = self.platform_logos[platform_name]
                logo_x = ctx.image.width - self.PADDING - logo.width
                logo_y = ctx.y_pos + (self.AVATAR_SIZE - logo.height) // 2
                ctx.image.paste(logo, (logo_x, logo_y), logo)

        ctx.y_pos += self.AVATAR_SIZE + self.SECTION_SPACING

    def _load_avatar(self, avatar_path: Path | None) -> PILImage:
        """加载头像（带圆形裁剪）"""
        if avatar_path and avatar_path.exists():
            try:
                with Image.open(avatar_path) as img:
                    avatar = img.convert("RGBA").resize((self.AVATAR_SIZE, self.AVATAR_SIZE), Image.Resampling.LANCZOS)
            except Exception:
                avatar = self._create_avatar_placeholder()
        else:
            avatar = self._create_avatar_placeholder()

        # 圆形遮罩
        mask = Image.new("L", (self.AVATAR_SIZE, self.AVATAR_SIZE), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1), fill=255)
        avatar.putalpha(mask)
        return avatar

    def _create_avatar_placeholder(self) -> PILImage:
        """创建默认头像"""
        size = self.AVATAR_SIZE
        placeholder = Image.new("RGBA", (size, size), (230, 230, 230, 255))
        draw = ImageDraw.Draw(placeholder)

        # 简单的人形图标
        center = size // 2
        head_r = size // 6
        draw.ellipse(
            (center - head_r, size * 35 // 100 - head_r, center + head_r, size * 35 // 100 + head_r),
            fill=(200, 200, 200, 255),
        )
        draw.ellipse(
            (center - size * 27 // 100, size * 55 // 100, center + size * 27 // 100, size * 115 // 100),
            fill=(200, 200, 200, 255),
        )
        return placeholder

    async def _render_title(self, ctx: RenderContext) -> None:
        """渲染标题"""
        if not ctx.result.title:
            return

        lines = self._wrap_text(ctx.result.title, ctx.content_width, self.fontset.title)
        ctx.y_pos += await self._draw_text_lines(ctx, lines, self.fontset.title)
        ctx.y_pos += self.SECTION_SPACING

    async def _render_cover_or_images(self, ctx: RenderContext) -> None:
        """渲染封面或图片网格"""
        # 尝试封面
        cover_path = await ctx.result.cover_path
        if cover_path and cover_path.exists():
            cover = self._load_cover(cover_path, ctx.content_width)
            if cover:
                x_pos = self.PADDING
                ctx.image.paste(cover, (x_pos, ctx.y_pos))
                # 视频按钮
                btn_size = 128
                btn_x = x_pos + (cover.width - btn_size) // 2
                btn_y = ctx.y_pos + (cover.height - btn_size) // 2
                ctx.image.paste(self.video_button_image, (btn_x, btn_y), self.video_button_image)
                ctx.y_pos += cover.height + self.SECTION_SPACING
                return

        # 尝试图片网格
        if ctx.result.img_contents:
            await self._render_image_grid(ctx)
            return

        # 尝试图文内容
        if ctx.result.graphics_contents:
            for gc in ctx.result.graphics_contents:
                await self._render_graphics(ctx, gc)

    def _load_cover(self, cover_path: Path, content_width: int) -> PILImage | None:
        """加载并缩放封面"""
        try:
            with Image.open(cover_path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                # 缩放到内容宽度
                if img.width != content_width:
                    ratio = content_width / img.width
                    new_h = int(img.height * ratio)
                    if new_h > self.MAX_COVER_HEIGHT:
                        ratio = self.MAX_COVER_HEIGHT / new_h
                        new_h = self.MAX_COVER_HEIGHT
                        content_width = int(content_width * ratio)
                    return img.resize((content_width, new_h), Image.Resampling.LANCZOS)
                return img.copy()
        except Exception as e:
            logger.debug(f"加载封面失败: {e}")
            return None

    async def _render_image_grid(self, ctx: RenderContext) -> None:
        """渲染图片网格"""
        contents = ctx.result.img_contents
        total = len(contents)
        has_more = total > self.MAX_IMAGES_DISPLAY
        display_contents = contents[: self.MAX_IMAGES_DISPLAY]

        images: list[PILImage] = []
        for content in display_contents:
            try:
                path = await content.get_path()
                img = self._load_grid_image(path, ctx.content_width, len(display_contents))
                if img:
                    images.append(img)
            except Exception:
                continue

        if not images:
            return

        count = len(images)
        cols = 1 if count == 1 else (2 if count in (2, 4) else self.IMAGE_GRID_COLS)
        rows = (count + cols - 1) // cols

        # 计算尺寸
        if count == 1:
            img_size = ctx.content_width
        else:
            num_gaps = cols + 1
            max_size = self.IMAGE_2_GRID_SIZE if cols == 2 else self.IMAGE_3_GRID_SIZE
            img_size = min((ctx.content_width - self.IMAGE_GRID_SPACING * num_gaps) // cols, max_size)

        spacing = self.IMAGE_GRID_SPACING
        current_y = ctx.y_pos

        for row in range(rows):
            row_start = row * cols
            row_imgs = images[row_start : row_start + cols]
            max_h = max(img.height for img in row_imgs)

            for i, img in enumerate(row_imgs):
                img_x = self.PADDING + spacing + i * (img_size + spacing)
                img_y = current_y + spacing + (max_h - img.height) // 2
                ctx.image.paste(img, (img_x, img_y))

                # +N 指示器
                if has_more and row == rows - 1 and i == len(row_imgs) - 1:
                    remaining = total - self.MAX_IMAGES_DISPLAY
                    self._draw_more_indicator(ctx.image, img_x, current_y + spacing, img.width, img.height, remaining)

            current_y += spacing + max_h

        ctx.y_pos = current_y + spacing + self.SECTION_SPACING

    def _load_grid_image(self, path: Path, content_width: int, count: int) -> PILImage | None:
        """加载网格图片"""
        try:
            with Image.open(path) as img:
                # 多图裁剪为方形
                if count >= 2:
                    w, h = img.size
                    if w != h:
                        s = min(w, h)
                        left = (w - s) // 2
                        top = (h - s) // 2
                        img = img.crop((left, top, left + s, top + s))

                # 计算目标尺寸
                if count == 1:
                    target = (content_width, min(self.MAX_IMAGE_HEIGHT, content_width))
                else:
                    cols = 2 if count in (2, 4) else self.IMAGE_GRID_COLS
                    max_size = self.IMAGE_2_GRID_SIZE if cols == 2 else self.IMAGE_3_GRID_SIZE
                    num_gaps = cols + 1
                    size = min((content_width - self.IMAGE_GRID_SPACING * num_gaps) // cols, max_size)
                    target = (size, size)

                if img.width > target[0] or img.height > target[1]:
                    ratio = min(target[0] / img.width, target[1] / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    return img.resize(new_size, Image.Resampling.LANCZOS)
                return img.copy()
        except Exception:
            return None

    def _draw_more_indicator(self, image: PILImage, x: int, y: int, w: int, h: int, count: int) -> None:
        """绘制 +N 指示器"""
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 100))
        image.paste(overlay, (x, y), overlay)

        text = f"+{count}"
        font = self.fontset.indicator
        text_w = font.get_text_width(text)
        text_x = x + (w - text_w) // 2
        text_y = y + (h - font.line_height) // 2
        ImageDraw.Draw(image).text((text_x, text_y), text, fill=font.fill, font=font.font)

    async def _render_graphics(self, ctx: RenderContext, gc: GraphicsContent) -> None:
        """渲染图文内容"""
        try:
            path = await gc.get_path()
            with Image.open(path) as img:
                if img.width > ctx.content_width:
                    ratio = ctx.content_width / img.width
                    img = img.resize((ctx.content_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
                else:
                    img = img.copy()

            # 计算所需高度并确保画布足够
            text_height = 0
            if gc.text:
                lines = self._wrap_text(gc.text, ctx.content_width, self.fontset.text)
                text_height = len(lines) * self.fontset.text.line_height + self.SECTION_SPACING
            alt_height = self.fontset.extra.line_height + self.SECTION_SPACING if gc.alt else 0
            needed = text_height + img.height + alt_height + self.SECTION_SPACING
            self._ensure_canvas_height(ctx, needed)

            # 文本
            if gc.text:
                lines = self._wrap_text(gc.text, ctx.content_width, self.fontset.text)
                ctx.y_pos += await self._draw_text_lines(ctx, lines, self.fontset.text)
                ctx.y_pos += self.SECTION_SPACING

            # 图片
            x_pos = self.PADDING + (ctx.content_width - img.width) // 2
            ctx.image.paste(img, (x_pos, ctx.y_pos))
            ctx.y_pos += img.height

            # Alt 文本
            if gc.alt:
                ctx.y_pos += self.SECTION_SPACING
                text_w = self.fontset.extra.get_text_width(gc.alt)
                text_x = self.PADDING + (ctx.content_width - text_w) // 2
                ctx.draw.text((text_x, ctx.y_pos), gc.alt, font=self.fontset.extra.font, fill=self.fontset.extra.fill)
                ctx.y_pos += self.fontset.extra.line_height

            ctx.y_pos += self.SECTION_SPACING
        except Exception as e:
            logger.debug(f"渲染图文失败: {e}")

    async def _render_text(self, ctx: RenderContext) -> None:
        """渲染正文"""
        if not ctx.result.text:
            return

        lines = self._wrap_text(ctx.result.text, ctx.content_width, self.fontset.text)
        ctx.y_pos += await self._draw_text_lines(ctx, lines, self.fontset.text)
        ctx.y_pos += self.SECTION_SPACING

    async def _render_extra(self, ctx: RenderContext) -> None:
        """渲染额外信息"""
        if not ctx.result.extra_info:
            return

        lines = self._wrap_text(ctx.result.extra_info, ctx.content_width, self.fontset.extra)
        ctx.y_pos += await self._draw_text_lines(ctx, lines, self.fontset.extra)

    async def _render_repost(self, ctx: RenderContext) -> None:
        """渲染转发内容"""
        if not ctx.result.repost:
            return

        # 递归渲染转发内容
        repost_img = await self._create_card_image(ctx.result.repost, False)

        # 缩放
        scaled_w = int(repost_img.width * self.REPOST_SCALE)
        scaled_h = int(repost_img.height * self.REPOST_SCALE)
        repost_img = repost_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

        # 容器
        container_h = scaled_h + self.REPOST_PADDING * 2
        x1, y1 = self.PADDING, ctx.y_pos
        x2, y2 = self.PADDING + ctx.content_width, ctx.y_pos + container_h

        # 背景和边框
        ctx.draw.rounded_rectangle(
            (x1, y1, x2, y2), radius=8, fill=self.REPOST_BG_COLOR, outline=self.REPOST_BORDER_COLOR
        )

        # 居中贴图
        card_x = x1 + (ctx.content_width - scaled_w) // 2
        card_y = y1 + self.REPOST_PADDING
        ctx.image.paste(repost_img, (card_x, card_y))

        ctx.y_pos += container_h + self.SECTION_SPACING

    async def _draw_text_lines(self, ctx: RenderContext, lines: list[str], font: FontInfo) -> int:
        """绘制多行文本"""
        if not lines:
            return 0

        xy = (self.PADDING, ctx.y_pos)
        if emosvg is not None:
            emosvg.text(ctx.image, xy, lines, font.font, fill=font.fill, line_height=font.line_height)
        else:
            await Apilmoji.text(
                ctx.image, xy, lines, font.font, fill=font.fill, line_height=font.line_height, source=self.EMOJI_SOURCE
            )
        return font.line_height * len(lines)

    def _wrap_text(self, text: str, max_width: int, font: FontInfo) -> list[str]:
        """文本自动换行"""
        if not text:
            return []

        def is_punctuation(c: str) -> bool:
            return c in "，。！？；：、）】》〉」』〕〗〙〛…—·,.;:!?)]}"

        lines: list[str] = []

        for paragraph in text.splitlines():
            if not paragraph:
                lines.append("")
                continue

            current_line = ""
            current_width = 0
            idx = 0

            emoji_list = emoji.emoji_list(paragraph)
            while idx < len(paragraph):
                # 检查 emoji
                for ed in emoji_list:
                    if ed["match_start"] == idx:
                        char = ed["emoji"]
                        idx = ed["match_end"]
                        char_width = font.font.size
                        break
                else:
                    char = paragraph[idx]
                    idx += 1
                    char_width = font.get_char_width_fast(char)

                if not current_line:
                    current_line = char
                    current_width = char_width
                    continue

                if len(char) == 1 and is_punctuation(char):
                    current_line += char
                    current_width += char_width
                    continue

                if current_width + char_width <= max_width:
                    current_line += char
                    current_width += char_width
                else:
                    lines.append(current_line)
                    current_line = char
                    current_width = char_width

            if current_line:
                lines.append(current_line)

        return lines
