from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar
from typing_extensions import override

from PIL import Image, ImageDraw, ImageFont

from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class CommonRenderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    # 卡片配置常量
    PADDING = 20
    AVATAR_SIZE = 80
    MAX_COVER_WIDTH = 1000
    MAX_COVER_HEIGHT = 800
    DEFAULT_CARD_WIDTH = 800
    SECTION_SPACING = 15

    # 颜色配置
    BG_COLOR = (255, 255, 255)
    TEXT_COLOR = (51, 51, 51)
    HEADER_COLOR = (0, 122, 255)
    EXTRA_COLOR = (136, 136, 136)

    ITEM_NAMES = ("name", "title", "text", "extra")
    # 字体大小和行高
    FONT_SIZES: ClassVar[dict[str, int]] = {"name": 28, "title": 24, "text": 30, "extra": 24}
    LINE_HEIGHTS: ClassVar[dict[str, int]] = {"name": 32, "title": 28, "text": 36, "extra": 28}
    # 预加载的字体（在类定义后立即加载）
    FONTS: ClassVar[dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]]

    @override
    async def render_messages(self, result: ParseResult):
        # 生成图片卡片
        image_raw = await self.draw_common_image(result)
        if image_raw:
            yield UniMessage([UniHelper.img_seg(raw=image_raw)])

        # 渲染其他内容
        async for message in self.render_contents(result):
            yield message

    async def draw_common_image(self, result: ParseResult) -> bytes | None:
        """使用 PIL 绘制通用社交媒体帖子卡片

        Args:
            result: 解析结果

        Returns:
            PNG 图片的字节数据，如果没有足够的内容则返回 None
        """
        # 如果既没有标题, 文本也没有封面，不生成图片
        if not result.title and not result.text:
            return None

        # 使用预加载的字体
        fonts = self.FONTS

        # 加载并处理封面
        cover_img = self._load_and_resize_cover(await result.cover_path)

        # 计算卡片宽度
        card_width = cover_img.width + 2 * self.PADDING if cover_img else self.DEFAULT_CARD_WIDTH
        content_width = card_width - 2 * self.PADDING

        # 计算各部分内容的高度
        heights = await self._calculate_sections(result, cover_img, content_width, fonts)

        # 计算总高度
        card_height = sum(h for _, h, _ in heights) + self.PADDING * 2 + self.SECTION_SPACING * (len(heights) - 1)

        # 创建画布并绘制
        image = Image.new("RGB", (card_width, card_height), self.BG_COLOR)
        self._draw_sections(image, heights, card_width, fonts)

        # 将图片转换为字节
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def _load_and_resize_cover(self, cover_path: Path | None) -> Image.Image | None:
        """加载并调整封面尺寸"""
        if not cover_path or not cover_path.exists():
            return None

        cover_img = Image.open(cover_path)

        # 如果封面太大，需要缩放
        if cover_img.width > self.MAX_COVER_WIDTH or cover_img.height > self.MAX_COVER_HEIGHT:
            width_ratio = self.MAX_COVER_WIDTH / cover_img.width
            height_ratio = self.MAX_COVER_HEIGHT / cover_img.height
            scale_ratio = min(width_ratio, height_ratio)

            new_width = int(cover_img.width * scale_ratio)
            new_height = int(cover_img.height * scale_ratio)
            cover_img = cover_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return cover_img

    def _load_and_process_avatar(self, avatar: Path | None) -> Image.Image | None:
        """加载并处理头像（圆形裁剪，带抗锯齿）"""
        if not avatar:
            return None

        avatar_img = None
        try:
            if avatar and avatar.exists():
                avatar_img = Image.open(avatar)

            if not avatar_img:
                return None

            # 转换为 RGBA 模式（用于更好的抗锯齿效果）
            if avatar_img.mode != "RGBA":
                avatar_img = avatar_img.convert("RGBA")

            # 使用超采样技术提高质量：先放大到 2 倍
            scale = 2
            temp_size = self.AVATAR_SIZE * scale
            avatar_img = avatar_img.resize((temp_size, temp_size), Image.Resampling.LANCZOS)

            # 创建高分辨率圆形遮罩（带抗锯齿）
            mask = Image.new("L", (temp_size, temp_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            # 使用抗锯齿绘制圆形
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
        self, result: ParseResult, cover_img: Image.Image | None, content_width: int, fonts: dict
    ) -> list[tuple[str, int, Any]]:
        """计算各部分内容的高度和数据"""
        heights = []

        # 1. Header 部分
        if result.author:
            header_data = await self._calculate_header_section(result, content_width, fonts)
            if header_data:
                heights.append(("header", header_data["height"], header_data))

        # 2. 标题部分
        if result.title:
            title_lines = self._wrap_text(result.title, content_width, fonts["title"])
            title_height = len(title_lines) * self.LINE_HEIGHTS["title"]
            heights.append(("title", title_height, title_lines))

        # 3. 封面部分
        if cover_img:
            heights.append(("cover", cover_img.height, cover_img))

        # 4. 文本内容
        if result.text:
            text_lines = self._wrap_text(result.text, content_width, fonts["text"])
            text_height = len(text_lines) * self.LINE_HEIGHTS["text"]
            heights.append(("text", text_height, text_lines))

        # 5. 额外信息
        if result.extra_info:
            extra_lines = self._wrap_text(result.extra_info, content_width, fonts["extra"])
            extra_height = len(extra_lines) * self.LINE_HEIGHTS["extra"]
            heights.append(("extra", extra_height, extra_lines))

        return heights

    async def _calculate_header_section(self, result: ParseResult, content_width: int, fonts: dict) -> dict | None:
        """计算 header 部分的高度和内容"""
        if not result.author:
            return None

        # 加载头像
        avatar_img = self._load_and_process_avatar(await result.author.avatar_path)

        # 计算文字区域宽度（始终预留头像空间）
        text_area_width = content_width - (self.AVATAR_SIZE + 15)

        # 发布者名称
        name_lines = self._wrap_text(result.author.name, text_area_width, fonts["name"])

        # 时间
        time_text = result.formart_datetime() if result.timestamp else ""
        time_lines = self._wrap_text(time_text, text_area_width, fonts["extra"]) if time_text else []

        # 计算 header 高度（取头像和文字中较大者）
        text_height = len(name_lines) * self.LINE_HEIGHTS["name"] + (
            len(time_lines) * self.LINE_HEIGHTS["extra"] + 5 if time_lines else 0
        )
        header_height = max(self.AVATAR_SIZE, text_height)

        return {
            "height": header_height,
            "avatar": avatar_img,
            "name_lines": name_lines,
            "time_lines": time_lines,
            "text_height": text_height,
        }

    def _draw_sections(
        self, image: Image.Image, heights: list[tuple[str, int, Any]], card_width: int, fonts: dict
    ) -> None:
        """绘制所有内容到画布上"""
        draw = ImageDraw.Draw(image)
        y_pos = self.PADDING

        for section_type, height, content in heights:
            if section_type == "header":
                y_pos = self._draw_header(image, draw, content, y_pos, fonts)
            elif section_type == "title":
                y_pos = self._draw_title(draw, content, y_pos, fonts["title"])
            elif section_type == "cover":
                y_pos = self._draw_cover(image, content, y_pos, card_width)
            elif section_type == "text":
                y_pos = self._draw_text(draw, content, y_pos, fonts["text"])
            elif section_type == "extra":
                y_pos = self._draw_extra(draw, content, y_pos, fonts["extra"])

    def _draw_header(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, content: dict, y_pos: int, fonts: dict
    ) -> int:
        """绘制 header 部分"""
        x_pos = self.PADDING

        # 绘制头像或占位符
        if content["avatar"]:
            image.paste(content["avatar"], (x_pos, y_pos), content["avatar"])
        else:
            # 绘制默认头像占位符（淡灰色圆形）
            placeholder = Image.new("RGBA", (self.AVATAR_SIZE, self.AVATAR_SIZE), (0, 0, 0, 0))
            placeholder_draw = ImageDraw.Draw(placeholder)

            # 绘制圆形背景
            placeholder_draw.ellipse((0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1), fill=(230, 230, 230, 255))

            # 绘制简单的用户图标（圆形头部 + 肩部）
            center_x = self.AVATAR_SIZE // 2

            # 头部圆形（较小，不会超出）
            head_radius = self.AVATAR_SIZE // 6
            head_y = int(self.AVATAR_SIZE * 0.35)
            placeholder_draw.ellipse(
                (
                    center_x - head_radius,
                    head_y - head_radius,
                    center_x + head_radius,
                    head_y + head_radius,
                ),
                fill=(200, 200, 200, 255),
            )

            # 肩部（确保不超出圆形边界）
            shoulder_y = int(self.AVATAR_SIZE * 0.55)
            shoulder_width = int(self.AVATAR_SIZE * 0.55)
            shoulder_height = int(self.AVATAR_SIZE * 0.6)
            placeholder_draw.ellipse(
                (
                    center_x - shoulder_width // 2,
                    shoulder_y,
                    center_x + shoulder_width // 2,
                    shoulder_y + shoulder_height,
                ),
                fill=(200, 200, 200, 255),
            )

            # 创建圆形遮罩确保不超出边界
            mask = Image.new("L", (self.AVATAR_SIZE, self.AVATAR_SIZE), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1), fill=255)

            # 应用遮罩
            placeholder.putalpha(mask)
            image.paste(placeholder, (x_pos, y_pos), placeholder)

        # 文字始终从头像位置后面开始（占位）
        text_x = self.PADDING + self.AVATAR_SIZE + 15

        # 计算文字垂直居中位置（对齐头像中轴）
        avatar_center = y_pos + self.AVATAR_SIZE // 2
        text_start_y = avatar_center - content["text_height"] // 2
        text_y = text_start_y

        # 发布者名称（蓝色）
        for line in content["name_lines"]:
            draw.text((text_x, text_y), line, fill=self.HEADER_COLOR, font=fonts["name"])
            text_y += self.LINE_HEIGHTS["name"]

        # 时间（灰色）
        if content["time_lines"]:
            text_y += 5
            for line in content["time_lines"]:
                draw.text((text_x, text_y), line, fill=self.EXTRA_COLOR, font=fonts["extra"])
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
        x_pos = (card_width - cover_img.width) // 2
        image.paste(cover_img, (x_pos, y_pos))
        return y_pos + cover_img.height + self.SECTION_SPACING

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

    def _wrap_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> list[str]:
        """文本自动换行

        Args:
            text: 要处理的文本
            max_width: 最大宽度（像素）
            font: 字体

        Returns:
            换行后的文本列表
        """
        lines = []
        paragraphs = text.split("\n")

        for paragraph in paragraphs:
            if not paragraph:
                lines.append("")
                continue

            words = paragraph
            current_line = ""

            for char in words:
                test_line = current_line + char
                # 使用 getbbox 计算文本宽度
                bbox = font.getbbox(test_line)
                width = bbox[2] - bbox[0]

                if width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char

            if current_line:
                lines.append(current_line)

        return lines if lines else [""]

    @classmethod
    def load_fonts(cls):
        """根据系统加载字体"""

        from platform import system

        os_type = system()

        fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]
        if os_type == "Darwin":  # macOS
            fonts = cls._load_macos_fonts()
        elif os_type == "Windows":  # Windows
            fonts = cls._load_windows_fonts()
        elif os_type == "Linux":  # Linux
            fonts = cls._load_linux_fonts()
        else:
            # 未知系统，使用默认字体
            default_font = ImageFont.load_default()
            fonts = dict.fromkeys(cls.ITEM_NAMES, default_font)

        cls.FONTS = fonts

    @classmethod
    def _load_macos_fonts(cls) -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
        """加载 macOS 字体"""
        # 优先尝试 PingFang（苹方）
        font_candidates = [
            Path("/System/Library/Fonts/PingFang.ttc"),
        ]

        for font_path in font_candidates:
            if font_path.exists():
                try:
                    return {
                        item_name: ImageFont.truetype(font_path, cls.FONT_SIZES[item_name])
                        for item_name in cls.ITEM_NAMES
                    }
                except OSError:
                    continue

        # 所有字体都失败，返回默认字体
        default_font = ImageFont.load_default()
        return dict.fromkeys(cls.ITEM_NAMES, default_font)

    @classmethod
    def _load_windows_fonts(cls) -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
        """加载 Windows 字体"""
        # Windows 字体路径
        windows_fonts_path = Path("C:/Windows/Fonts")

        # 优先尝试微软雅黑，然后是黑体，最后是宋体
        font_candidates = [
            windows_fonts_path / "msyh.ttc",  # 微软雅黑
            windows_fonts_path / "msyhbd.ttc",  # 微软雅黑 Bold
            windows_fonts_path / "msyh.ttf",  # 微软雅黑（旧版本）
            windows_fonts_path / "simhei.ttf",  # 黑体
            windows_fonts_path / "simsun.ttc",  # 宋体
            windows_fonts_path / "arial.ttf",  # Arial（英文）
        ]

        # 尝试加载粗体和普通字体
        bold_font_candidates = [
            windows_fonts_path / "msyhbd.ttc",  # 微软雅黑粗体
            windows_fonts_path / "arialbd.ttf",  # Arial Bold
        ]

        # 先尝试加载普通字体
        normal_font = None
        for font_path in font_candidates:
            if font_path.exists():
                normal_font = font_path
                break

        # 尝试加载粗体字体用于名称
        bold_font = None
        for font_path in bold_font_candidates:
            if font_path.exists():
                bold_font = font_path
                break

        # 如果没有找到粗体，使用普通字体
        if not bold_font:
            bold_font = normal_font

        # 如果找到了字体，尝试加载
        if normal_font and bold_font:
            try:
                return {
                    "name": ImageFont.truetype(str(bold_font), cls.FONT_SIZES["name"]),
                    "title": ImageFont.truetype(str(normal_font), cls.FONT_SIZES["title"]),
                    "text": ImageFont.truetype(str(normal_font), cls.FONT_SIZES["text"]),
                    "extra": ImageFont.truetype(str(normal_font), cls.FONT_SIZES["extra"]),
                }
            except OSError:
                pass

        # 所有字体都失败，返回默认字体
        default_font = ImageFont.load_default()
        return dict.fromkeys(cls.ITEM_NAMES, default_font)

    @classmethod
    def _load_linux_fonts(cls) -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
        """加载 Linux 字体"""
        # Linux 常见字体路径
        font_candidates = [
            # DejaVu 字体（最常见）
            (
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ),
            # Ubuntu 字体
            (
                Path("/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"),
                Path("/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"),
            ),
            # Liberation 字体
            (
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            ),
            # Noto 字体（支持中文）
            (
                Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
                Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            ),
            (
                Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
                Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            ),
        ]

        for bold_path, normal_path in font_candidates:
            if bold_path.exists() and normal_path.exists():
                try:
                    return {
                        "name": ImageFont.truetype(bold_path, cls.FONT_SIZES["name"]),
                        "title": ImageFont.truetype(normal_path, cls.FONT_SIZES["title"]),
                        "text": ImageFont.truetype(normal_path, cls.FONT_SIZES["text"]),
                        "extra": ImageFont.truetype(normal_path, cls.FONT_SIZES["extra"]),
                    }
                except OSError:
                    continue

        # 所有字体都失败，返回默认字体
        default_font = ImageFont.load_default()
        return dict.fromkeys(cls.ITEM_NAMES, default_font)
