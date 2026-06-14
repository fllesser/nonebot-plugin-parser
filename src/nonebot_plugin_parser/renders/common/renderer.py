from io import BytesIO
from typing import ClassVar
from pathlib import Path
from typing_extensions import override

import emoji
from PIL import Image, ImageDraw, ImageFont
from nonebot import logger
from apilmoji import Apilmoji

from . import assets
from .. import resources
from .font import StyledFont, FontMetrics
from ..base import ParseResult, ImageContent, ImageRenderer

Color = tuple[int, int, int]
PILImage = Image.Image
PILImageDraw = ImageDraw.ImageDraw

try:
    import emosvg
except ImportError:
    emosvg = None
except OSError:
    logger.error("未安装 cairo, 无法使用 emosvg 渲染 emoji")
    emosvg = None


class CommonRenderer(ImageRenderer):
    """统一渲染器"""

    # 布局常量
    PADDING = 25
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
    SUBREDDIT_ICON_SIZE = 32

    # 颜色
    BG_COLOR: ClassVar[Color] = (255, 255, 255)
    REPOST_BG_COLOR: ClassVar[Color] = (247, 247, 247)
    REPOST_BORDER_COLOR: ClassVar[Color] = (230, 230, 230)

    def __init__(self, result: ParseResult, not_repost: bool = True):
        super().__init__(result, not_repost)
        assets.ensure_resources()

        self.card_width: int = self.DEFAULT_CARD_WIDTH
        self.content_width: int = self.card_width - 2 * self.PADDING
        self.y_pos: int = self.PADDING

        self._image: PILImage
        self._draw: PILImageDraw

        if result.repost:
            self.repost_renderer = CommonRenderer(
                result.repost,
                False,
            )

    @override
    async def render_image(self) -> bytes:
        image = await self._render_image()
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    async def _render_image(self) -> PILImage:
        """渲染图片 (内部方法)"""
        from ...translate import apply_card_translation

        await apply_card_translation(self.result)
        estimated_height = self._estimate_height()
        bg_color = self.BG_COLOR if self.not_repost else self.REPOST_BG_COLOR

        self._image = Image.new("RGB", (self.card_width, estimated_height), bg_color)
        self._draw = ImageDraw.Draw(self._image)

        # 单次遍历渲染各部分
        await self._render_header()
        await self._render_title()
        await self._render_main_content()
        await self._render_text()
        await self._render_extra()
        await self._render_repost()

        # 裁剪到实际高度
        final_height = self.y_pos + self.PADDING
        logger.debug(f"估算高度: {estimated_height}, 画布高度: {self._image.height}, 最终高度: {final_height}")
        return self._image.crop((0, 0, self.card_width, final_height))

    def _estimate_text_height(
        self,
        text: str,
        metrics: FontMetrics,
        content_width: int,
    ) -> int:
        """估算文本高度（考虑换行符）"""
        return (text.count("\n") + 1 + len(text) * metrics.cjk_width // content_width) * metrics.line_height

    def _estimate_height(self) -> int:
        """估算画布高度"""
        # 上下边距
        height = self.PADDING * 2

        # 头部
        if self.result.platform.name == "reddit" and self.result.extra.get("subreddit_prefixed"):
            height += self.SUBREDDIT_ICON_SIZE + self.SECTION_SPACING
            if self.result.author:
                height += assets.AVATAR_SIZE + self.SECTION_SPACING
        elif self.result.author:
            height += assets.AVATAR_SIZE + self.SECTION_SPACING

        # 标题
        if self.result.title:
            height += self._estimate_text_height(
                self.result.title,
                assets.FONTS.title.metrics,
                self.content_width,
            )
            height += self.SECTION_SPACING

        # 图文内容
        if graphics := self.result.graphics:
            for item in graphics:
                if isinstance(item, str):
                    height += self._estimate_text_height(
                        item,
                        assets.FONTS.body.metrics,
                        self.content_width,
                    )
                else:
                    height += self.MAX_COVER_HEIGHT
            height += (len(graphics) - 1) * self.SECTION_SPACING
        # 封面或图片
        else:
            height += self.MAX_COVER_HEIGHT + self.SECTION_SPACING

        # 简介
        if self.result.text:
            height += self._estimate_text_height(
                self.result.text,
                assets.FONTS.body.metrics,
                self.content_width,
            )
            height += self.SECTION_SPACING

        # 额外信息
        if self.result.extra_info:
            height += self._estimate_text_height(
                self.result.extra_info,
                assets.FONTS.muted.metrics,
                self.content_width,
            )
            height += self.SECTION_SPACING

        # 转发内容
        if self.result.repost:
            height += int(self.repost_renderer._estimate_height() * self.REPOST_SCALE)
            height += self.REPOST_PADDING * 2 + self.SECTION_SPACING

        return height

    async def _render_header(self) -> None:
        """渲染头部"""
        if self.result.platform.name == "reddit" and self.result.extra.get("subreddit_prefixed"):
            await self._render_reddit_subreddit_header()
            if self.result.author:
                await self._render_reddit_op_row()
            return
        if self.result.author is None:
            return

        x_pos = self.PADDING

        # 头像
        if avatar := self.result.author.avatar:
            avatar_path = await self.result.author.avatar.safe_get()
            avatar = self._load_avatar(avatar_path)
            self._image.paste(avatar, (x_pos, self.y_pos), avatar)

        # 文字区域
        text_x = self.PADDING + assets.AVATAR_SIZE + self.AVATAR_TEXT_GAP
        name_height = assets.FONTS.name.metrics.line_height
        time_str = self.result.formartted_datetime
        time_height = (self.NAME_TIME_GAP + assets.FONTS.muted.metrics.line_height) if time_str else 0
        text_height = name_height + time_height

        # 垂直居中
        text_y = self.y_pos + (assets.AVATAR_SIZE - text_height) // 2

        # 名称
        self._draw.text(
            (text_x, text_y),
            self.result.author.name,
            font=assets.FONTS.name.metrics.font,
            fill=assets.FONTS.name.fill,
        )
        text_y += name_height

        # 时间
        if time_str:
            text_y += self.NAME_TIME_GAP
            self._draw.text(
                (text_x, text_y),
                time_str,
                font=assets.FONTS.muted.metrics.font,
                fill=assets.FONTS.muted.fill,
            )

        # 平台 Logo
        if self.not_repost:
            platform_name = self.result.platform.name
            if platform_name in assets.PLATFORM_LOGOS:
                logo = self._resize_platform_logo(platform_name, assets.PLATFORM_LOGOS[platform_name])
                logo_x = self._image.width - self.PADDING - logo.width
                logo_y = self.y_pos + (assets.AVATAR_SIZE - logo.height) // 2
                self._image.paste(logo, (logo_x, logo_y), logo)

        self.y_pos += assets.AVATAR_SIZE + self.SECTION_SPACING

    def _load_avatar(self, avatar_path: Path | None) -> PILImage:
        """加载头像（带圆形裁剪）"""
        if avatar_path is None or not avatar_path.exists():
            return assets.AVATAR_IMAGE

        try:
            with Image.open(avatar_path) as img:
                avatar = img.convert("RGBA")
                avatar = avatar.resize(
                    (assets.AVATAR_SIZE, assets.AVATAR_SIZE),
                    Image.Resampling.LANCZOS,
                )
        except Exception:
            return assets.AVATAR_IMAGE

        # 圆形遮罩
        mask = Image.new("L", (assets.AVATAR_SIZE, assets.AVATAR_SIZE), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, assets.AVATAR_SIZE - 1, assets.AVATAR_SIZE - 1), fill=255)
        avatar.putalpha(mask)
        return avatar


    async def _render_reddit_subreddit_header(self) -> None:
        """Reddit 卡片左上角：版块图标 + r/子版块名"""
        x_pos = self.PADDING
        size = self.SUBREDDIT_ICON_SIZE
        gap = 8
        label = str(self.result.extra.get("subreddit_prefixed", ""))

        icon_task = self.result.extra.get("subreddit_icon")
        if icon_task is not None:
            icon_path = await icon_task.safe_get()
            icon = self._load_subreddit_icon(icon_path, size)
            self._image.paste(icon, (x_pos, self.y_pos), icon)
            x_pos += size + gap

        metrics = assets.FONTS.name.metrics
        text_y = self.y_pos + (size - metrics.line_height) // 2

        logo_reserved = 0
        if self.not_repost and self.result.platform.name in assets.PLATFORM_LOGOS:
            logo = self._resize_platform_logo(self.result.platform.name, assets.PLATFORM_LOGOS[self.result.platform.name])
            logo_w = logo.width
            logo_reserved = logo_w + 8

        max_label_w = max(40, self.content_width - (x_pos - self.PADDING) - logo_reserved)
        if hasattr(self, "_truncate_text_to_width"):
            label = self._truncate_text_to_width(label, max_label_w, metrics)

        self._draw.text(
            (x_pos, text_y),
            label,
            font=metrics.font,
            fill=assets.FONTS.name.fill,
        )

        if self.not_repost and self.result.platform.name in assets.PLATFORM_LOGOS:
            logo = self._resize_platform_logo(self.result.platform.name, assets.PLATFORM_LOGOS[self.result.platform.name])
            logo_x = self._image.width - self.PADDING - logo.width
            logo_y = self.y_pos + (size - logo.height) // 2
            self._image.paste(logo, (logo_x, logo_y), logo)

        self.y_pos += size + self.SECTION_SPACING




    async def _render_reddit_op_row(self) -> None:
        """Reddit 卡片：版块行下方展示 OP 头像、用户名、发帖时间"""
        author = self.result.author
        if author is None:
            return

        x_pos = self.PADDING

        if author.avatar:
            avatar_path = await author.avatar.safe_get()
            avatar_img = self._load_avatar(avatar_path)
            self._image.paste(avatar_img, (x_pos, self.y_pos), avatar_img)

        text_x = self.PADDING + assets.AVATAR_SIZE + self.AVATAR_TEXT_GAP
        name_height = assets.FONTS.name.metrics.line_height
        time_str = self.result.formartted_datetime
        time_height = (
            self.NAME_TIME_GAP + assets.FONTS.muted.metrics.line_height
        ) if time_str else 0
        text_height = name_height + time_height
        text_y = self.y_pos + (assets.AVATAR_SIZE - text_height) // 2

        self._draw.text(
            (text_x, text_y),
            author.name,
            font=assets.FONTS.name.metrics.font,
            fill=assets.FONTS.name.fill,
        )
        text_y += name_height

        if time_str:
            text_y += self.NAME_TIME_GAP
            self._draw.text(
                (text_x, text_y),
                time_str,
                font=assets.FONTS.muted.metrics.font,
                fill=assets.FONTS.muted.fill,
            )

        self.y_pos += assets.AVATAR_SIZE + self.SECTION_SPACING

    def _load_subreddit_icon(self, icon_path: Path | None, size: int) -> PILImage:
        if icon_path is None or not icon_path.exists():
            return assets.AVATAR_IMAGE.resize((size, size), Image.Resampling.LANCZOS)
        try:
            with Image.open(icon_path) as img:
                icon = img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        except Exception:
            return assets.AVATAR_IMAGE.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        icon.putalpha(mask)
        return icon

    async def _render_title(self) -> None:
        """渲染标题"""
        if not self.result.title:
            return

        lines = self._wrap_text(
            self.result.title,
            self.content_width,
            assets.FONTS.title.metrics,
        )
        self.y_pos += await self._draw_text(lines, assets.FONTS.title)
        self.y_pos += self.SECTION_SPACING

    async def _render_main_content(self) -> None:
        """渲染封面/图片网格/图文内容"""
        if cover := await self._load_cover():
            # 视频时长
            self._image.paste(cover, (self.PADDING, self.y_pos))
            self.y_pos += cover.height + self.SECTION_SPACING
            return

        # 图片网格
        if self.result.contents:
            await self._render_image_grid()
            return

        # 无媒体时仍显示占位封面（避免只有标题的窄条卡片）
        if self.result.extra.get("post_removed") or (
            not self.result.graphics and self.result.extra.get("info")
        ):
            from .. import resources
            with resources.random_fallback_pic().open("rb") as _f:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(_f.read())).convert("RGBA")
            content_width = self.content_width
            if img.width != content_width:
                ratio = content_width / img.width
                img = img.resize((content_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
            self._image.paste(img, (self.PADDING, self.y_pos), img)
            self.y_pos += img.height + self.SECTION_SPACING
            return

        # 图文内容
        if graphics := self.result.graphics:
            for item in graphics:
                if isinstance(item, str):
                    await self._render_text(item)
                else:
                    await self._render_img_in_graphics(item)

    async def _load_cover(self) -> PILImage | None:
        """加载并缩放封面"""
        if self.result.video is None:
            return None

        cover_path = None
        if cover_task := self.result.video.cover:
            cover_path = await cover_task.safe_get()

        if cover_path is None:
            return Image.open(resources.random_fallback_pic())

        with Image.open(cover_path) as img:
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # 缩放到内容宽度
            content_width = self.content_width
            if img.width != content_width:
                ratio = content_width / img.width
                new_h = int(img.height * ratio)
                if new_h > self.MAX_COVER_HEIGHT:
                    ratio = self.MAX_COVER_HEIGHT / new_h
                    new_h = self.MAX_COVER_HEIGHT
                    content_width = int(content_width * ratio)
                img = img.resize(
                    (content_width, new_h),
                    Image.Resampling.LANCZOS,
                )

            # 视频播放按钮
            btn_size = 100
            btn_x, btn_y = (img.width - btn_size) // 2, (img.height - btn_size) // 2
            img.paste(
                assets.VIDEO_BUTTON_IMAGE,
                (btn_x, btn_y),
                assets.VIDEO_BUTTON_IMAGE,
            )

            # 视频时长
            # display_duration = video_content.display_duration

            # paint = assets.FONTS.muted
            # text_width = font.get_text_width(display_duration)
            # # 计算文本绘制位置
            # text_x = img.width - text_width - 20
            # text_y = img.height - 50

            # # 根据文本位置和大小计算矩形范围，确保文本居中
            # padding = 4
            # rect_x1 = text_x - padding
            # rect_y1 = text_y - padding
            # rect_x2 = text_x + text_width + padding
            # rect_y2 = text_y + font.line_height + padding

            # # 创建一个临时的半透明图层
            # overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            # ImageDraw.Draw(overlay).rounded_rectangle(
            #     (rect_x1, rect_y1, rect_x2, rect_y2),
            #     radius=8,
            #     fill=(51, 51, 51, 204),
            # )
            # # 将半透明图层合成到原图
            # img = Image.alpha_composite(img, overlay)

            # ImageDraw.Draw(img).text(
            #     (text_x, text_y),
            #     display_duration,
            #     font=paint.metrics.font,
            #     fill=paint.fill,
            # )

            return img.copy()

    async def _render_image_grid(self) -> None:
        """渲染图片网格"""
        grid_images = self.result.all_grid_images
        if not grid_images:
            return

        total = len(grid_images)
        has_more = total > self.MAX_IMAGES_DISPLAY
        display_contents = grid_images[: self.MAX_IMAGES_DISPLAY]

        images: list[PILImage] = []
        for content in display_contents:
            path = await content.safe_get()
            if path is None or not path.exists():
                path = resources.random_fallback_pic()
            if img := self._load_grid_image(path, len(display_contents)):
                images.append(img)

        if not images:
            return

        count = len(images)
        cols = 1 if count == 1 else (2 if count in (2, 4) else self.IMAGE_GRID_COLS)
        rows = (count + cols - 1) // cols

        # 计算尺寸
        if count == 1:
            img_size = self.content_width
        else:
            num_gaps = cols + 1
            max_size = self.IMAGE_2_GRID_SIZE if cols == 2 else self.IMAGE_3_GRID_SIZE
            img_size = min((self.content_width - self.IMAGE_GRID_SPACING * num_gaps) // cols, max_size)

        spacing = self.IMAGE_GRID_SPACING
        current_y = self.y_pos

        for row in range(rows):
            row_start = row * cols
            row_imgs = images[row_start : row_start + cols]
            max_h = max(img.height for img in row_imgs)

            for i, img in enumerate(row_imgs):
                img_x = self.PADDING + spacing + i * (img_size + spacing)
                img_y = current_y + spacing + (max_h - img.height) // 2
                self._image.paste(img, (img_x, img_y))

                # +N 指示器
                if has_more and row == rows - 1 and i == len(row_imgs) - 1:
                    remaining = total - self.MAX_IMAGES_DISPLAY
                    self._draw_more_indicator(
                        self._image,
                        img_x,
                        current_y + spacing,
                        img.width,
                        img.height,
                        remaining,
                    )

            current_y += spacing + max_h

        self.y_pos = current_y + spacing + self.SECTION_SPACING

    def _load_grid_image(self, path: Path, count: int) -> PILImage | None:
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
                    target = (self.content_width, min(self.MAX_IMAGE_HEIGHT, self.content_width))
                else:
                    cols = 2 if count in (2, 4) else self.IMAGE_GRID_COLS
                    max_size = self.IMAGE_2_GRID_SIZE if cols == 2 else self.IMAGE_3_GRID_SIZE
                    num_gaps = cols + 1
                    size = min((self.content_width - self.IMAGE_GRID_SPACING * num_gaps) // cols, max_size)
                    target = (size, size)

                if img.width > target[0] or img.height > target[1]:
                    ratio = min(target[0] / img.width, target[1] / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    return img.resize(new_size, Image.Resampling.LANCZOS)
                return img.copy()
        except Exception:
            return None

    def _draw_more_indicator(
        self,
        image: PILImage,
        x: int,
        y: int,
        w: int,
        h: int,
        count: int,
    ) -> None:
        """绘制 +N 指示器"""
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 100))
        image.paste(overlay, (x, y), overlay)

        indicator_text = f"+{count}"
        font_size, color = 60, (255, 255, 255)
        # 这里统一使用默认字体
        font = ImageFont.truetype(resources.DEFAULT_FONT_PATH, font_size)
        text_w = font.getbbox(indicator_text)[2]
        text_x = x + (w - text_w) // 2
        text_y = y + (h - font_size) // 2
        ImageDraw.Draw(image).text((text_x, text_y), indicator_text, fill=color, font=font)

    async def _render_img_in_graphics(self, image_content: ImageContent) -> None:
        """渲染图片"""
        path = await image_content.path_task.safe_get()
        if path is None or not path.exists():
            path = resources.random_fallback_pic()

        with Image.open(path) as img:
            if img.width > self.content_width:
                ratio = self.content_width / img.width
                img = img.resize(
                    (self.content_width, int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            else:
                img = img.copy()

        x_pos = self.PADDING + (self.content_width - img.width) // 2
        self._image.paste(img, (x_pos, self.y_pos))
        self.y_pos += img.height

        # Alt 文本
        if image_content.alt:
            self.y_pos += self.SECTION_SPACING
            paint = assets.FONTS.muted
            text_w = paint.metrics.get_text_width(image_content.alt)
            text_x = self.PADDING + (self.content_width - text_w) // 2
            self._draw.text(
                (text_x, self.y_pos),
                image_content.alt,
                font=paint.metrics.font,
                fill=paint.fill,
            )
            self.y_pos += paint.metrics.line_height

        self.y_pos += self.SECTION_SPACING

    async def _render_text(self, text: str | None = None) -> None:
        """渲染正文"""
        text = text or self.result.text
        if not text:
            return

        lines = self._wrap_text(
            text,
            self.content_width,
            assets.FONTS.body.metrics,
        )
        self.y_pos += await self._draw_text(lines, assets.FONTS.body)
        self.y_pos += self.SECTION_SPACING

    async def _render_extra(self) -> None:
        """渲染额外信息"""
        if not self.result.extra_info:
            return

        lines = self._wrap_text(
            self.result.extra_info,
            self.content_width,
            assets.FONTS.muted.metrics,
        )
        self.y_pos += await self._draw_text(lines, assets.FONTS.muted)

    async def _render_repost(self) -> None:
        """渲染转发内容"""
        if not self.result.repost:
            return

        # 递归渲染转发内容
        repost_img = await self.repost_renderer._render_image()

        # 缩放
        scaled_w = int(repost_img.width * self.REPOST_SCALE)
        scaled_h = int(repost_img.height * self.REPOST_SCALE)
        repost_img = repost_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

        # 容器
        container_h = scaled_h + self.REPOST_PADDING * 2
        x1, y1 = self.PADDING, self.y_pos
        x2, y2 = self.PADDING + self.content_width, self.y_pos + container_h

        # 背景和边框
        self._draw.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=8,
            fill=self.REPOST_BG_COLOR,
            outline=self.REPOST_BORDER_COLOR,
        )

        # 居中贴图
        card_x = x1 + (self.content_width - scaled_w) // 2
        card_y = y1 + self.REPOST_PADDING
        self._image.paste(repost_img, (card_x, card_y))
        self.y_pos += container_h + self.SECTION_SPACING

    async def _draw_text(self, lines: list[str], styled: StyledFont) -> int:
        """绘制多行文本"""
        if not lines:
            return 0

        metrics = styled.metrics
        xy = (self.PADDING, self.y_pos)
        if emosvg is not None:
            emosvg.text(
                self._image,
                xy,
                lines,
                metrics.font,
                fill=styled.fill,
                line_height=metrics.line_height,
            )
        else:
            await Apilmoji.text(
                self._image,
                xy,
                lines,
                metrics.font,
                fill=styled.fill,
                line_height=metrics.line_height,
                source=assets.EMOJI_SOURCE,
            )
        return metrics.line_height * len(lines)

    def _wrap_text(self, text: str, max_width: int, metrics: FontMetrics) -> list[str]:
        """文本自动换行"""
        if not text:
            return []

        # 去掉 制表符
        text = text.replace("\t", " ")
        # 去掉 变体选择符
        text = text.replace(chr(65039), "")

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
                        char_width = metrics.font.size
                        break
                else:
                    char = paragraph[idx]
                    idx += 1
                    char_width = metrics.get_char_width_fast(char)

                if not current_line:
                    current_line = char
                    current_width = char_width
                    continue

                if len(char) == 1 and self.is_trailing_punctuation(char):
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

    @staticmethod
    def is_trailing_punctuation(c: str) -> bool:
        """判断是否可作为行尾的标点符号"""
        return c in "，。！？；：、）】》〉」』〕〗〙〛…—·,.;:!?)]}"
    # 卡片右上角平台 logo（reddit.png 原图很大，需限制高度）
    PLATFORM_LOGO_HEADER_HEIGHT = 30
    PLATFORM_LOGO_HEADER_HEIGHTS: ClassVar[dict[str, int]] = {
        "reddit": 30,
    }
    PLATFORM_LOGO_HEADER_WIDTHS: ClassVar[dict[str, int]] = {
        "instagram": 240,
    }


    def _resize_platform_logo(self, platform_name: str, logo: PILImage) -> PILImage:
        target_w = self.PLATFORM_LOGO_HEADER_WIDTHS.get(platform_name)
        if target_w and logo.width != target_w:
            return logo.resize(
                (target_w, max(1, int(logo.height * target_w / max(logo.width, 1)))),
                Image.Resampling.LANCZOS,
            )
        target_h = self._platform_logo_header_height(platform_name)
        if logo.height > target_h:
            return logo.resize(
                (max(1, int(logo.width * target_h / logo.height)), target_h),
                Image.Resampling.LANCZOS,
            )
        return logo

    def _platform_logo_header_height(self, platform_name: str) -> int:
        return self.PLATFORM_LOGO_HEADER_HEIGHTS.get(
            platform_name,
            getattr(self, "PLATFORM_LOGO_HEADER_HEIGHT", 30),
        )
