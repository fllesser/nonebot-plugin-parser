from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar
from typing_extensions import override

from nonebot import logger
from PIL import Image, ImageDraw, ImageFont

from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class CommonRenderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    __slots__ = ("font_path", "fonts")

    # 卡片配置常量
    PADDING = 25
    AVATAR_SIZE = 80
    AVATAR_TEXT_GAP = 15  # 头像和文字之间的间距
    MAX_COVER_WIDTH = 1000
    MAX_COVER_HEIGHT = 800
    DEFAULT_CARD_WIDTH = 800
    MIN_CARD_WIDTH = 400  # 最小卡片宽度，确保头像、名称、时间显示正常
    SECTION_SPACING = 15
    NAME_TIME_GAP = 5  # 名称和时间之间的间距

    # 头像占位符配置
    AVATAR_PLACEHOLDER_BG_COLOR = (230, 230, 230, 255)
    AVATAR_PLACEHOLDER_FG_COLOR = (200, 200, 200, 255)
    AVATAR_HEAD_RATIO = 0.35  # 头部位置比例
    AVATAR_HEAD_RADIUS_RATIO = 1 / 6  # 头部半径比例
    AVATAR_SHOULDER_Y_RATIO = 0.55  # 肩部 Y 位置比例
    AVATAR_SHOULDER_WIDTH_RATIO = 0.55  # 肩部宽度比例
    AVATAR_SHOULDER_HEIGHT_RATIO = 0.6  # 肩部高度比例

    # 颜色配置
    BG_COLOR = (255, 255, 255)
    TEXT_COLOR = (51, 51, 51)
    HEADER_COLOR = (0, 122, 255)
    EXTRA_COLOR = (136, 136, 136)

    # 转发内容配置
    REPOST_BG_COLOR = (247, 247, 247)  # 转发背景色
    REPOST_BORDER_COLOR = (230, 230, 230)  # 转发边框色
    REPOST_PADDING = 12  # 转发内容内边距

    # 图片处理配置
    MIN_COVER_WIDTH = 300  # 最小封面宽度
    MIN_COVER_HEIGHT = 200  # 最小封面高度
    MAX_IMAGE_HEIGHT = 800  # 图片最大高度限制
    MAX_IMAGE_GRID_SIZE = 300  # 图片网格最大尺寸
    IMAGE_GRID_SPACING = 4  # 图片网格间距
    MAX_IMAGES_DISPLAY = 9  # 最大显示图片数量
    IMAGE_GRID_COLS = 3  # 图片网格列数
    IMAGE_GRID_ROWS_SINGLE = 1  # 单张图片行数
    IMAGE_GRID_COLS_SINGLE = 1  # 单张图片列数

    # 视频播放按钮配置
    VIDEO_BUTTON_SIZE_RATIO = 0.25  # 播放按钮大小比例（相对于封面）
    VIDEO_BUTTON_ALPHA = 120  # 播放按钮透明度
    VIDEO_TRIANGLE_SIZE_RATIO = 0.33  # 三角形大小比例（相对于按钮）

    # 头像处理配置
    AVATAR_UPSCALE_FACTOR = 2  # 头像超采样倍数

    # 转发缩放配置
    REPOST_SCALE = 0.88  # 转发内容缩放比例

    ITEM_NAMES = ("name", "title", "text", "extra")
    # 字体大小和行高
    FONT_SIZES: ClassVar[dict[str, int]] = {"name": 28, "title": 30, "text": 24, "extra": 24}
    LINE_HEIGHTS: ClassVar[dict[str, int]] = {"name": 32, "title": 36, "text": 28, "extra": 28}

    DEFAULT_FONT_PATH: ClassVar[Path] = Path(__file__).parent / "fonts" / "HYSongYunLangHeiW-1.ttf"

    def __init__(self, font_path: Path | None = None):
        self.font_path: Path = self.DEFAULT_FONT_PATH

    def load_font(self, font_path: Path | None = None):
        if font_path is not None and font_path.exists():
            self.font_path = font_path
        self.fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {
            name: ImageFont.truetype(self.font_path, size) for name, size in self.FONT_SIZES.items()
        }
        logger.success(f"加载字体「{self.font_path.name}」成功")

    @override
    async def render_messages(self, result: ParseResult):
        # 生成图片卡片
        if image_raw := await self.draw_common_image(result):
            msg = UniMessage(UniHelper.img_seg(raw=image_raw))
            if self.append_url:
                urls = (result.display_url, result.repost_display_url)
                msg += "\n".join(url for url in urls if url)
            yield msg

        # 媒体内容
        async for message in self.render_contents(result):
            yield message

    async def draw_common_image(self, result: ParseResult) -> bytes | None:
        """使用 PIL 绘制通用社交媒体帖子卡片

        Args:
            result: 解析结果

        Returns:
            PNG 图片的字节数据，如果没有足够的内容则返回 None
        """
        # 调用内部方法生成图片
        image = await self._create_card_image(result)
        if not image:
            return None

        # 将图片转换为字节
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    async def _create_card_image(
        self, result: ParseResult, bg_color: tuple[int, int, int] | None = None, apply_min_cover_size: bool = True
    ) -> Image.Image | None:
        """创建卡片图片（内部方法，用于递归调用）

        Args:
            result: 解析结果
            bg_color: 背景颜色，默认使用 BG_COLOR
            apply_min_cover_size: 是否对封面应用最小尺寸限制，转发内容不需要

        Returns:
            PIL Image 对象，如果没有足够的内容则返回 None
        """
        # 使用预加载的字体

        # 先确定固定的卡片宽度和内容区域宽度
        card_width = max(self.DEFAULT_CARD_WIDTH, self.MIN_CARD_WIDTH)
        content_width = card_width - 2 * self.PADDING

        # 加载并处理封面，传入内容区域宽度以确保封面不超过内容区域
        cover_img = self._load_and_resize_cover(
            await result.cover_path, content_width=content_width, apply_min_size=apply_min_cover_size
        )

        # 计算各部分内容的高度
        heights = await self._calculate_sections(result, cover_img, content_width)

        # 计算总高度
        card_height = sum(h for _, h, _ in heights) + self.PADDING * 2 + self.SECTION_SPACING * (len(heights) - 1)
        # 创建画布并绘制（使用指定的背景颜色，或默认背景颜色）
        background_color = bg_color if bg_color is not None else self.BG_COLOR
        image = Image.new("RGB", (card_width, card_height), background_color)
        self._draw_sections(image, heights, card_width)

        return image

    def _load_and_resize_cover(
        self, cover_path: Path | None, content_width: int, apply_min_size: bool = True
    ) -> Image.Image | None:
        """加载并调整封面尺寸

        Args:
            cover_path: 封面路径
            content_width: 内容区域宽度，封面会缩放到此宽度以确保左右padding一致
            apply_min_size: 是否应用最小尺寸限制（转发内容不需要）
        """
        if not cover_path or not cover_path.exists():
            return None

        try:
            cover_img = Image.open(cover_path)

            # 转换为 RGB 模式以确保兼容性
            if cover_img.mode not in ("RGB", "RGBA"):
                cover_img = cover_img.convert("RGB")

            # 封面宽度应该等于内容区域宽度，以确保左右padding一致
            target_width = content_width

            # 计算缩放比例（保持宽高比）
            if cover_img.width != target_width:
                scale_ratio = target_width / cover_img.width
                new_width = target_width
                new_height = int(cover_img.height * scale_ratio)

                # 检查高度是否超过最大限制
                if new_height > self.MAX_COVER_HEIGHT:
                    # 如果高度超限，按高度重新计算
                    scale_ratio = self.MAX_COVER_HEIGHT / new_height
                    new_height = self.MAX_COVER_HEIGHT
                    new_width = int(new_width * scale_ratio)

                # 如果是主内容且高度太小，需要放大（但不超过最大高度）
                if apply_min_size and new_height < self.MIN_COVER_HEIGHT:
                    min_height = min(self.MIN_COVER_HEIGHT, self.MAX_COVER_HEIGHT)
                    if new_height < min_height:
                        scale_ratio = min_height / new_height
                        new_height = min_height
                        new_width = int(new_width * scale_ratio)
                        # 再次确保宽度不超过内容区域
                        if new_width > content_width:
                            scale_ratio = content_width / new_width
                            new_width = content_width
                            new_height = int(new_height * scale_ratio)

                cover_img = cover_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            return cover_img
        except Exception:
            # 加载失败时返回 None
            return None

    def _load_and_process_avatar(self, avatar: Path | None) -> Image.Image | None:
        """加载并处理头像（圆形裁剪，带抗锯齿）"""
        if not avatar or not avatar.exists():
            return None

        try:
            avatar_img = Image.open(avatar)

            # 转换为 RGBA 模式（用于更好的抗锯齿效果）
            if avatar_img.mode != "RGBA":
                avatar_img = avatar_img.convert("RGBA")

            # 使用超采样技术提高质量：先放大到指定倍数
            scale = self.AVATAR_UPSCALE_FACTOR
            temp_size = self.AVATAR_SIZE * scale
            avatar_img = avatar_img.resize((temp_size, temp_size), Image.Resampling.LANCZOS)

            # 创建高分辨率圆形遮罩（带抗锯齿）
            mask = Image.new("L", (temp_size, temp_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, temp_size - 1, temp_size - 1), fill=255)

            # 应用遮罩
            output_avatar = Image.new("RGBA", (temp_size, temp_size), (0, 0, 0, 0))
            output_avatar.paste(avatar_img, (0, 0))
            output_avatar.putalpha(mask)

            # 缩小到目标尺寸（抗锯齿缩放）
            output_avatar = output_avatar.resize((self.AVATAR_SIZE, self.AVATAR_SIZE), Image.Resampling.LANCZOS)

            return output_avatar
        except Exception:
            return None

    async def _calculate_sections(
        self, result: ParseResult, cover_img: Image.Image | None, content_width: int
    ) -> list[tuple[str, int, Any]]:
        """计算各部分内容的高度和数据"""
        heights = []

        # 1. Header 部分
        if result.author:
            header_data = await self._calculate_header_section(result, content_width)
            if header_data:
                heights.append(("header", header_data["height"], header_data))

        # 2. 标题部分
        if result.title:
            title_lines = self._wrap_text(result.title, content_width, self.fonts["title"])
            title_height = len(title_lines) * self.LINE_HEIGHTS["title"]
            heights.append(("title", title_height, title_lines))

        # 3. 封面部分
        if cover_img:
            heights.append(("cover", cover_img.height, cover_img))
        elif result.img_contents:
            # 如果没有封面但有图片，处理图片列表
            img_grid_data = await self._calculate_image_grid_section(result, content_width)
            if img_grid_data:
                heights.append(("image_grid", img_grid_data["height"], img_grid_data))

        # 4. 文本内容
        if result.text:
            text_lines = self._wrap_text(result.text, content_width, self.fonts["text"])
            text_height = len(text_lines) * self.LINE_HEIGHTS["text"]
            heights.append(("text", text_height, text_lines))

        # 5. 额外信息
        if result.extra_info:
            extra_lines = self._wrap_text(result.extra_info, content_width, self.fonts["extra"])
            extra_height = len(extra_lines) * self.LINE_HEIGHTS["extra"]
            heights.append(("extra", extra_height, extra_lines))

        # 6. 转发内容
        if result.repost:
            repost_data = await self._calculate_repost_section(result.repost, content_width)
            if repost_data:
                heights.append(("repost", repost_data["height"], repost_data))

        return heights

    async def _calculate_header_section(self, result: ParseResult, content_width: int) -> dict | None:
        """计算 header 部分的高度和内容"""
        if not result.author:
            return None

        # 加载头像
        avatar_img = self._load_and_process_avatar(await result.author.get_avatar_path())

        # 计算文字区域宽度（始终预留头像空间）
        text_area_width = content_width - (self.AVATAR_SIZE + self.AVATAR_TEXT_GAP)

        # 发布者名称
        name_lines = self._wrap_text(result.author.name, text_area_width, self.fonts["name"])

        # 时间
        time_text = result.formartted_datetime
        time_lines = self._wrap_text(time_text, text_area_width, self.fonts["extra"]) if time_text else []

        # 计算 header 高度（取头像和文字中较大者）
        text_height = len(name_lines) * self.LINE_HEIGHTS["name"]
        if time_lines:
            text_height += self.NAME_TIME_GAP + len(time_lines) * self.LINE_HEIGHTS["extra"]
        header_height = max(self.AVATAR_SIZE, text_height)

        return {
            "height": header_height,
            "avatar": avatar_img,
            "name_lines": name_lines,
            "time_lines": time_lines,
            "text_height": text_height,
        }

    async def _calculate_repost_section(self, repost: ParseResult, content_width: int) -> dict | None:
        """计算转发内容的高度和内容（递归调用绘制方法）"""
        if not repost:
            return None

        # 递归调用内部方法，生成转发内容的完整卡片（使用转发背景颜色，不强制放大封面）
        repost_image = await self._create_card_image(repost, bg_color=self.REPOST_BG_COLOR, apply_min_cover_size=False)
        if not repost_image:
            return None

        # 缩放图片
        scaled_width = int(repost_image.width * self.REPOST_SCALE)
        scaled_height = int(repost_image.height * self.REPOST_SCALE)
        repost_image_scaled = repost_image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

        return {
            "height": scaled_height + self.REPOST_PADDING * 2,  # 加上转发容器的内边距
            "scaled_image": repost_image_scaled,
        }

    async def _calculate_image_grid_section(self, result: ParseResult, content_width: int) -> dict | None:
        """计算图片网格部分的高度和内容"""
        if not result.img_contents:
            return None

        # 检查是否有超过最大显示数量的图片
        total_images = len(result.img_contents)
        has_more = total_images > self.MAX_IMAGES_DISPLAY

        # 如果超过最大显示数量，处理前N张，最后一张显示+N效果
        if has_more:
            img_contents = result.img_contents[: self.MAX_IMAGES_DISPLAY]
            remaining_count = total_images - self.MAX_IMAGES_DISPLAY
        else:
            img_contents = result.img_contents[: self.MAX_IMAGES_DISPLAY]
            remaining_count = 0

        processed_images = []

        for img_content in img_contents:
            try:
                img_path = await img_content.get_path()
                if img_path and img_path.exists():
                    img = Image.open(img_path)

                    # 根据图片数量决定处理方式
                    if len(img_contents) >= 2:
                        # 2张及以上图片，统一为方形
                        img = self._crop_to_square(img)

                    # 调整图片尺寸
                    if len(img_contents) == 1:
                        # 单张图片，根据卡片宽度调整，与视频封面保持一致
                        max_width = content_width
                        max_height = min(self.MAX_IMAGE_HEIGHT, content_width)  # 限制最大高度
                        if img.width > max_width or img.height > max_height:
                            ratio = min(max_width / img.width, max_height / img.height)
                            new_size = (int(img.width * ratio), int(img.height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                    else:
                        # 多张图片，使用网格布局
                        # 计算图片尺寸，确保左右间距相同：间距 + (图片 + 间距) * 列数 = 总宽度
                        num_gaps = self.IMAGE_GRID_COLS + 1  # 3列有4个间距
                        max_size = (content_width - self.IMAGE_GRID_SPACING * num_gaps) // self.IMAGE_GRID_COLS
                        max_size = min(max_size, self.MAX_IMAGE_GRID_SIZE)
                        if img.width > max_size or img.height > max_size:
                            ratio = min(max_size / img.width, max_size / img.height)
                            new_size = (int(img.width * ratio), int(img.height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)

                    processed_images.append(img)
            except Exception:
                continue

        if not processed_images:
            return None

        # 计算网格布局
        if len(processed_images) == 1:
            # 单张图片，使用1列布局
            cols = self.IMAGE_GRID_COLS_SINGLE
            rows = self.IMAGE_GRID_ROWS_SINGLE
        else:
            # 多张图片，统一使用3列布局（九宫格）
            cols = self.IMAGE_GRID_COLS
            rows = (len(processed_images) + cols - 1) // cols

        # 计算高度
        max_img_height = max(img.height for img in processed_images)
        if len(processed_images) == 1:
            # 单张图片
            grid_height = max_img_height
        else:
            # 多张图片：上间距 + (图片 + 间距) * 行数
            grid_height = self.IMAGE_GRID_SPACING + rows * (max_img_height + self.IMAGE_GRID_SPACING)

        return {
            "height": grid_height,
            "images": processed_images,
            "cols": cols,
            "rows": rows,
            "has_more": has_more,
            "remaining_count": remaining_count,
        }

    def _crop_to_square(self, img: Image.Image) -> Image.Image:
        """将图片裁剪为方形（上下切割）"""
        width, height = img.size

        if width == height:
            return img

        if width > height:
            # 宽图片，左右切割
            left = (width - height) // 2
            right = left + height
            return img.crop((left, 0, right, height))
        else:
            # 高图片，上下切割
            top = (height - width) // 2
            bottom = top + width
            return img.crop((0, top, width, bottom))

    def _draw_sections(self, image: Image.Image, heights: list[tuple[str, int, Any]], card_width: int) -> None:
        """绘制所有内容到画布上"""
        draw = ImageDraw.Draw(image)
        y_pos = self.PADDING

        for section_type, height, content in heights:
            if section_type == "header":
                y_pos = self._draw_header(image, draw, content, y_pos)
            elif section_type == "title":
                y_pos = self._draw_title(draw, content, y_pos, self.fonts["title"])
            elif section_type == "cover":
                y_pos = self._draw_cover(image, content, y_pos, card_width)
            elif section_type == "text":
                y_pos = self._draw_text(draw, content, y_pos, self.fonts["text"])
            elif section_type == "extra":
                y_pos = self._draw_extra(draw, content, y_pos, self.fonts["extra"])
            elif section_type == "repost":
                y_pos = self._draw_repost(image, draw, content, y_pos, card_width)
            elif section_type == "image_grid":
                y_pos = self._draw_image_grid(image, content, y_pos, card_width)

    def _create_avatar_placeholder(self) -> Image.Image:
        """创建默认头像占位符"""
        placeholder = Image.new("RGBA", (self.AVATAR_SIZE, self.AVATAR_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(placeholder)

        # 绘制圆形背景
        draw.ellipse((0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1), fill=self.AVATAR_PLACEHOLDER_BG_COLOR)

        # 绘制简单的用户图标（圆形头部 + 肩部）
        center_x = self.AVATAR_SIZE // 2

        # 头部圆形
        head_radius = int(self.AVATAR_SIZE * self.AVATAR_HEAD_RADIUS_RATIO)
        head_y = int(self.AVATAR_SIZE * self.AVATAR_HEAD_RATIO)
        draw.ellipse(
            (
                center_x - head_radius,
                head_y - head_radius,
                center_x + head_radius,
                head_y + head_radius,
            ),
            fill=self.AVATAR_PLACEHOLDER_FG_COLOR,
        )

        # 肩部
        shoulder_y = int(self.AVATAR_SIZE * self.AVATAR_SHOULDER_Y_RATIO)
        shoulder_width = int(self.AVATAR_SIZE * self.AVATAR_SHOULDER_WIDTH_RATIO)
        shoulder_height = int(self.AVATAR_SIZE * self.AVATAR_SHOULDER_HEIGHT_RATIO)
        draw.ellipse(
            (
                center_x - shoulder_width // 2,
                shoulder_y,
                center_x + shoulder_width // 2,
                shoulder_y + shoulder_height,
            ),
            fill=self.AVATAR_PLACEHOLDER_FG_COLOR,
        )

        # 创建圆形遮罩确保不超出边界
        mask = Image.new("L", (self.AVATAR_SIZE, self.AVATAR_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1), fill=255)

        # 应用遮罩
        placeholder.putalpha(mask)
        return placeholder

    def _draw_header(self, image: Image.Image, draw: ImageDraw.ImageDraw, content: dict, y_pos: int) -> int:
        """绘制 header 部分"""
        x_pos = self.PADDING

        # 绘制头像或占位符
        avatar = content["avatar"] if content["avatar"] else self._create_avatar_placeholder()
        image.paste(avatar, (x_pos, y_pos), avatar)

        # 文字始终从头像位置后面开始
        text_x = self.PADDING + self.AVATAR_SIZE + self.AVATAR_TEXT_GAP

        # 计算文字垂直居中位置（对齐头像中轴）
        avatar_center = y_pos + self.AVATAR_SIZE // 2
        text_start_y = avatar_center - content["text_height"] // 2
        text_y = text_start_y

        # 发布者名称（蓝色）
        for line in content["name_lines"]:
            draw.text((text_x, text_y), line, fill=self.HEADER_COLOR, font=self.fonts["name"])
            text_y += self.LINE_HEIGHTS["name"]

        # 时间（灰色）
        if content["time_lines"]:
            text_y += self.NAME_TIME_GAP
            for line in content["time_lines"]:
                draw.text((text_x, text_y), line, fill=self.EXTRA_COLOR, font=self.fonts["extra"])
                text_y += self.LINE_HEIGHTS["extra"]

        return y_pos + content["height"] + self.SECTION_SPACING

    def _draw_title(self, draw: ImageDraw.ImageDraw, lines: list[str], y_pos: int, font) -> int:
        """绘制标题"""
        for line in lines:
            draw.text((self.PADDING, y_pos), line, fill=self.TEXT_COLOR, font=font)
            y_pos += self.LINE_HEIGHTS["title"]
        return y_pos + self.SECTION_SPACING

    def _draw_cover(self, image: Image.Image, cover_img: Image.Image, y_pos: int, card_width: int) -> int:
        """绘制封面"""
        # 封面从左边padding开始，和文字、头像对齐
        x_pos = self.PADDING
        image.paste(cover_img, (x_pos, y_pos))

        # 添加视频播放标志
        self._draw_video_play_button(image, x_pos, y_pos, cover_img.width, cover_img.height)

        return y_pos + cover_img.height + self.SECTION_SPACING

    def _draw_video_play_button(self, image: Image.Image, x_pos: int, y_pos: int, width: int, height: int):
        """在封面上绘制视频播放按钮"""
        draw = ImageDraw.Draw(image)

        # 计算播放按钮的位置和尺寸
        button_size = int(min(width, height) * self.VIDEO_BUTTON_SIZE_RATIO)  # 按钮大小比例
        button_x = x_pos + (width - button_size) // 2
        button_y = y_pos + (height - button_size) // 2

        # 绘制半透明圆形背景
        overlay = Image.new("RGBA", (button_size, button_size), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse((0, 0, button_size - 1, button_size - 1), fill=(0, 0, 0, self.VIDEO_BUTTON_ALPHA))

        # 将半透明背景贴到主画布上
        image.paste(overlay, (button_x, button_y), overlay)

        # 绘制播放三角形
        triangle_size = int(button_size * self.VIDEO_TRIANGLE_SIZE_RATIO)
        triangle_x = button_x + (button_size - triangle_size) // 2
        triangle_y = button_y + (button_size - triangle_size) // 2

        # 计算三角形的三个顶点（向右的三角形）
        triangle_points = [
            (triangle_x, triangle_y),  # 左上
            (triangle_x, triangle_y + triangle_size),  # 左下
            (triangle_x + triangle_size, triangle_y + triangle_size // 2),  # 右中
        ]

        # 绘制浅色三角形
        draw.polygon(triangle_points, fill=(255, 255, 255, 200))

    def _draw_text(self, draw: ImageDraw.ImageDraw, lines: list[str], y_pos: int, font) -> int:
        """绘制文本内容"""
        for line in lines:
            draw.text((self.PADDING, y_pos), line, fill=self.TEXT_COLOR, font=font)
            y_pos += self.LINE_HEIGHTS["text"]
        return y_pos + self.SECTION_SPACING

    def _draw_extra(self, draw: ImageDraw.ImageDraw, lines: list[str], y_pos: int, font) -> int:
        """绘制额外信息"""
        for line in lines:
            draw.text((self.PADDING, y_pos), line, fill=self.EXTRA_COLOR, font=font)
            y_pos += self.LINE_HEIGHTS["extra"]
        return y_pos

    def _draw_repost(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, content: dict, y_pos: int, card_width: int
    ) -> int:
        """绘制转发内容"""
        # 获取缩放后的转发图片
        repost_image = content["scaled_image"]

        # 转发框占满整个内容区域，左右和边缘对齐
        content_width = card_width - 2 * self.PADDING
        repost_x = self.PADDING
        repost_y = y_pos
        repost_width = content_width  # 转发框宽度等于内容区域宽度
        repost_height = content["height"]

        # 绘制转发背景（圆角矩形）
        self._draw_rounded_rectangle(
            image,
            (repost_x, repost_y, repost_x + repost_width, repost_y + repost_height),
            self.REPOST_BG_COLOR,
            radius=8,
        )

        # 绘制转发边框
        self._draw_rounded_rectangle_border(
            draw,
            (repost_x, repost_y, repost_x + repost_width, repost_y + repost_height),
            self.REPOST_BORDER_COLOR,
            radius=8,
            width=1,
        )

        # 转发图片在转发容器中居中
        card_x = repost_x + (repost_width - repost_image.width) // 2
        card_y = repost_y + self.REPOST_PADDING

        # 将缩放后的转发图片贴到主画布上
        image.paste(repost_image, (card_x, card_y))

        return y_pos + repost_height + self.SECTION_SPACING

    def _draw_image_grid(self, image: Image.Image, content: dict, y_pos: int, card_width: int) -> int:
        """绘制图片网格"""
        images = content["images"]
        cols = content["cols"]
        rows = content["rows"]
        has_more = content.get("has_more", False)
        remaining_count = content.get("remaining_count", 0)

        if not images:
            return y_pos

        # 计算每个图片的尺寸和间距
        available_width = card_width - 2 * self.PADDING  # 可用宽度
        img_spacing = self.IMAGE_GRID_SPACING

        # 根据图片数量计算每个图片的尺寸
        if len(images) == 1:
            # 单张图片，使用完整的可用宽度，与视频封面保持一致
            max_img_size = available_width
        else:
            # 多张图片，统一使用3列布局（九宫格）
            # 计算图片尺寸，确保所有间距相同
            num_gaps = cols + 1  # 3列有4个间距
            max_img_size = (available_width - img_spacing * num_gaps) // cols
            max_img_size = min(max_img_size, self.MAX_IMAGE_GRID_SIZE)

        current_y = y_pos

        for row in range(rows):
            row_start = row * cols
            row_end = min(row_start + cols, len(images))
            row_images = images[row_start:row_end]

            # 计算这一行的最大高度
            max_height = max(img.height for img in row_images)

            # 绘制这一行的图片
            for i, img in enumerate(row_images):
                # 每张图片左侧都有间距：间距 + (间距 + 图片) * i
                img_x = self.PADDING + img_spacing + i * (max_img_size + img_spacing)
                img_y = current_y + img_spacing  # 每行上方都有间距

                # 居中放置图片
                y_offset = (max_height - img.height) // 2
                image.paste(img, (img_x, img_y + y_offset))

                # 如果是最后一张图片且有更多图片，绘制+N效果
                if has_more and row == rows - 1 and i == len(row_images) - 1 and len(images) == self.MAX_IMAGES_DISPLAY:
                    self._draw_more_indicator(image, img_x, img_y, max_img_size, max_height, remaining_count)

            current_y += img_spacing + max_height

        return current_y + img_spacing + self.SECTION_SPACING

    def _draw_more_indicator(
        self, image: Image.Image, img_x: int, img_y: int, img_width: int, img_height: int, count: int
    ):
        """在图片上绘制+N指示器"""
        draw = ImageDraw.Draw(image)

        # 创建半透明黑色遮罩（透明度 1/4）
        overlay = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((0, 0, img_width - 1, img_height - 1), fill=(0, 0, 0, 100))

        # 将遮罩贴到图片上
        image.paste(overlay, (img_x, img_y), overlay)

        # 绘制+N文字
        text = f"+{count}"
        # 使用更大的字体
        font_size = min(img_width, img_height) // 4
        font = ImageFont.truetype(self.font_path, font_size)

        # 计算文字位置（居中）
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = img_x + (img_width - text_width) // 2
        text_y = img_y + (img_height - text_height) // 2

        # 绘制白色文字
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

    def _draw_rounded_rectangle(
        self, image: Image.Image, bbox: tuple[int, int, int, int], fill_color: tuple[int, int, int], radius: int = 8
    ):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = bbox
        draw = ImageDraw.Draw(image)

        # 绘制主体矩形
        draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill_color)
        draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill_color)

        # 绘制四个圆角
        draw.pieslice((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=fill_color)
        draw.pieslice((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=fill_color)
        draw.pieslice((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=fill_color)
        draw.pieslice((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=fill_color)

    def _draw_rounded_rectangle_border(
        self,
        draw: ImageDraw.ImageDraw,
        bbox: tuple[int, int, int, int],
        border_color: tuple[int, int, int],
        radius: int = 8,
        width: int = 1,
    ):
        """绘制圆角矩形边框"""
        x1, y1, x2, y2 = bbox

        # 绘制主体边框
        draw.rectangle((x1 + radius, y1, x2 - radius, y1 + width), fill=border_color)  # 上
        draw.rectangle((x1 + radius, y2 - width, x2 - radius, y2), fill=border_color)  # 下
        draw.rectangle((x1, y1 + radius, x1 + width, y2 - radius), fill=border_color)  # 左
        draw.rectangle((x2 - width, y1 + radius, x2, y2 - radius), fill=border_color)  # 右

        # 绘制四个圆角边框
        draw.arc((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=border_color, width=width)
        draw.arc((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=border_color, width=width)
        draw.arc((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=border_color, width=width)
        draw.arc((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=border_color, width=width)

    def _wrap_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> list[str]:
        """文本自动换行

        Args:
            text: 要处理的文本
            max_width: 最大宽度（像素）
            font: 字体

        Returns:
            换行后的文本列表
        """
        if not text:
            return [""]

        lines = []
        paragraphs = text.split("\n")

        for paragraph in paragraphs:
            if not paragraph:
                lines.append("")
                continue

            current_line = ""
            for char in paragraph:
                test_line = current_line + char
                # 使用 getbbox 计算文本宽度
                bbox = font.getbbox(test_line)
                width = bbox[2] - bbox[0]

                if width <= max_width:
                    current_line = test_line
                else:
                    # 如果当前行不为空，保存并开始新行
                    if current_line:
                        lines.append(current_line)
                        current_line = char
                    else:
                        # 单个字符就超宽，强制添加
                        lines.append(char)
                        current_line = ""

            # 保存最后一行
            if current_line:
                lines.append(current_line)

        return lines if lines else [""]
