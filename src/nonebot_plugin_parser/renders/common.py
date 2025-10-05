from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar
from typing_extensions import override

from PIL import Image, ImageDraw, ImageFont

from ..config import pconfig
from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class CommonRenderer(BaseRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    # 卡片配置常量
    PADDING = 20
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
    REPOST_AVATAR_SIZE = 32  # 转发头像尺寸
    REPOST_AVATAR_GAP = 8  # 转发头像和文字间距

    ITEM_NAMES = ("name", "title", "text", "extra")
    # 字体大小和行高
    FONT_SIZES: ClassVar[dict[str, int]] = {"name": 28, "title": 24, "text": 30, "extra": 24}
    LINE_HEIGHTS: ClassVar[dict[str, int]] = {"name": 32, "title": 28, "text": 36, "extra": 28}

    # 转发内容字体配置
    REPOST_FONT_SIZES: ClassVar[dict[str, int]] = {"repost_name": 14, "repost_text": 14, "repost_time": 12}
    REPOST_LINE_HEIGHTS: ClassVar[dict[str, int]] = {"repost_name": 16, "repost_text": 20, "repost_time": 14}
    # 预加载的字体（在类定义后立即加载）
    FONTS: ClassVar[dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]]

    @override
    async def render_messages(self, result: ParseResult):
        # 生成图片卡片
        if image_raw := await self.draw_common_image(result):
            msg = UniMessage(UniHelper.img_seg(raw=image_raw))
            if pconfig.append_url:
                urls = (result.display_url, result.repost_display_url)
                msg += "\n".join(urls)
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
        # 如果既没有标题, 文本也没有封面，不生成图片
        if not result.title and not result.text:
            return None

        # 使用预加载的字体
        fonts = self.FONTS

        # 加载并处理封面
        cover_img = self._load_and_resize_cover(await result.cover_path)

        # 计算卡片宽度
        if cover_img:
            card_width = max(cover_img.width + 2 * self.PADDING, self.MIN_CARD_WIDTH)
        else:
            card_width = max(self.DEFAULT_CARD_WIDTH, self.MIN_CARD_WIDTH)
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

        try:
            cover_img = Image.open(cover_path)

            # 转换为 RGB 模式以确保兼容性
            if cover_img.mode not in ("RGB", "RGBA"):
                cover_img = cover_img.convert("RGB")

            # 如果封面太大，需要缩放
            if cover_img.width > self.MAX_COVER_WIDTH or cover_img.height > self.MAX_COVER_HEIGHT:
                width_ratio = self.MAX_COVER_WIDTH / cover_img.width
                height_ratio = self.MAX_COVER_HEIGHT / cover_img.height
                scale_ratio = min(width_ratio, height_ratio)

                new_width = int(cover_img.width * scale_ratio)
                new_height = int(cover_img.height * scale_ratio)
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

            # 使用超采样技术提高质量：先放大到 2 倍
            scale = 2
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

        # 6. 转发内容
        if result.repost:
            repost_data = await self._calculate_repost_section(result.repost, content_width, fonts)
            if repost_data:
                heights.append(("repost", repost_data["height"], repost_data))

        return heights

    async def _calculate_header_section(self, result: ParseResult, content_width: int, fonts: dict) -> dict | None:
        """计算 header 部分的高度和内容"""
        if not result.author:
            return None

        # 加载头像
        avatar_img = self._load_and_process_avatar(await result.author.avatar_path)

        # 计算文字区域宽度（始终预留头像空间）
        text_area_width = content_width - (self.AVATAR_SIZE + self.AVATAR_TEXT_GAP)

        # 发布者名称
        name_lines = self._wrap_text(result.author.name, text_area_width, fonts["name"])

        # 时间
        time_text = result.formart_datetime() if result.timestamp else ""
        time_lines = self._wrap_text(time_text, text_area_width, fonts["extra"]) if time_text else []

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

    async def _calculate_repost_section(self, repost: ParseResult, content_width: int, fonts: dict) -> dict | None:
        """计算转发内容的高度和内容"""
        if not repost:
            return None

        # 转发内容区域宽度（减去内边距）
        repost_content_width = content_width - 2 * self.REPOST_PADDING

        # 计算转发头部高度
        repost_header_height = 0
        repost_avatar = None
        repost_name_lines = []
        repost_time_lines = []

        if repost.author:
            # 加载转发头像
            repost_avatar = self._load_and_process_repost_avatar(await repost.author.avatar_path)

            # 计算转发用户名
            name_area_width = repost_content_width - (self.REPOST_AVATAR_SIZE + self.REPOST_AVATAR_GAP)
            repost_name_lines = self._wrap_text(repost.author.name, name_area_width, fonts["repost_name"])

            # 计算转发时间
            if repost.timestamp:
                time_text = repost.formart_datetime()
                repost_time_lines = self._wrap_text(time_text, name_area_width, fonts["repost_time"])

            # 计算头部高度
            name_height = len(repost_name_lines) * self.REPOST_LINE_HEIGHTS["repost_name"]
            time_height = len(repost_time_lines) * self.REPOST_LINE_HEIGHTS["repost_time"] if repost_time_lines else 0
            repost_header_height = max(self.REPOST_AVATAR_SIZE, name_height + time_height)

        # 计算转发文本高度
        repost_text_height = 0
        repost_text_lines = []
        if repost.text:
            repost_text_lines = self._wrap_text(repost.text, repost_content_width, fonts["repost_text"])
            repost_text_height = len(repost_text_lines) * self.REPOST_LINE_HEIGHTS["repost_text"]

        # 计算转发媒体高度
        repost_media_height = 0
        repost_media_items = []
        if repost.img_contents:
            # 处理转发图片
            for img_content in repost.img_contents[:9]:  # 最多9张图片
                try:
                    img_path = await img_content.get_path()
                    if img_path and img_path.exists():
                        img = Image.open(img_path)
                        # 调整图片尺寸以适应转发区域
                        max_size = min(200, repost_content_width // 3)  # 转发图片较小
                        if img.width > max_size or img.height > max_size:
                            ratio = min(max_size / img.width, max_size / img.height)
                            new_size = (int(img.width * ratio), int(img.height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                        repost_media_items.append(img)
                except Exception:
                    continue

        # 计算总高度
        total_height = self.REPOST_PADDING * 2  # 上下内边距
        if repost_header_height > 0:
            total_height += repost_header_height + 8  # 头部高度 + 间距
        if repost_text_height > 0:
            total_height += repost_text_height + 8  # 文本高度 + 间距
        if repost_media_items:
            # 计算媒体网格高度
            cols = min(3, len(repost_media_items))
            rows = (len(repost_media_items) + cols - 1) // cols
            max_img_height = max(img.height for img in repost_media_items) if repost_media_items else 0
            repost_media_height = rows * max_img_height + (rows - 1) * 4  # 图片间距
            total_height += repost_media_height

        return {
            "height": total_height,
            "avatar": repost_avatar,
            "name_lines": repost_name_lines,
            "time_lines": repost_time_lines,
            "text_lines": repost_text_lines,
            "media_items": repost_media_items,
            "content_width": repost_content_width,
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
            elif section_type == "repost":
                y_pos = self._draw_repost(image, draw, content, y_pos, card_width, fonts)

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

    def _load_and_process_repost_avatar(self, avatar: Path | None) -> Image.Image | None:
        """加载并处理转发头像（小尺寸圆形）"""
        if not avatar or not avatar.exists():
            return None

        try:
            avatar_img = Image.open(avatar)

            # 转换为 RGBA 模式
            if avatar_img.mode != "RGBA":
                avatar_img = avatar_img.convert("RGBA")

            # 使用超采样技术提高质量
            scale = 2
            temp_size = self.REPOST_AVATAR_SIZE * scale
            avatar_img = avatar_img.resize((temp_size, temp_size), Image.Resampling.LANCZOS)

            # 创建高分辨率圆形遮罩
            mask = Image.new("L", (temp_size, temp_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, temp_size - 1, temp_size - 1), fill=255)

            # 应用遮罩
            output_avatar = Image.new("RGBA", (temp_size, temp_size), (0, 0, 0, 0))
            output_avatar.paste(avatar_img, (0, 0))
            output_avatar.putalpha(mask)

            # 缩小到目标尺寸
            output_avatar = output_avatar.resize(
                (self.REPOST_AVATAR_SIZE, self.REPOST_AVATAR_SIZE), Image.Resampling.LANCZOS
            )

            return output_avatar
        except Exception:
            return None

    def _create_repost_avatar_placeholder(self) -> Image.Image:
        """创建转发头像占位符"""
        placeholder = Image.new("RGBA", (self.REPOST_AVATAR_SIZE, self.REPOST_AVATAR_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(placeholder)

        # 绘制圆形背景
        draw.ellipse(
            (0, 0, self.REPOST_AVATAR_SIZE - 1, self.REPOST_AVATAR_SIZE - 1), fill=self.AVATAR_PLACEHOLDER_BG_COLOR
        )

        # 绘制简单的用户图标
        center_x = self.REPOST_AVATAR_SIZE // 2
        head_radius = int(self.REPOST_AVATAR_SIZE * self.AVATAR_HEAD_RADIUS_RATIO)
        head_y = int(self.REPOST_AVATAR_SIZE * self.AVATAR_HEAD_RATIO)
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
        shoulder_y = int(self.REPOST_AVATAR_SIZE * self.AVATAR_SHOULDER_Y_RATIO)
        shoulder_width = int(self.REPOST_AVATAR_SIZE * self.AVATAR_SHOULDER_WIDTH_RATIO)
        shoulder_height = int(self.REPOST_AVATAR_SIZE * self.AVATAR_SHOULDER_HEIGHT_RATIO)
        draw.ellipse(
            (
                center_x - shoulder_width // 2,
                shoulder_y,
                center_x + shoulder_width // 2,
                shoulder_y + shoulder_height,
            ),
            fill=self.AVATAR_PLACEHOLDER_FG_COLOR,
        )

        # 创建圆形遮罩
        mask = Image.new("L", (self.REPOST_AVATAR_SIZE, self.REPOST_AVATAR_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, self.REPOST_AVATAR_SIZE - 1, self.REPOST_AVATAR_SIZE - 1), fill=255)

        # 应用遮罩
        placeholder.putalpha(mask)
        return placeholder

    def _draw_header(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, content: dict, y_pos: int, fonts: dict
    ) -> int:
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
            draw.text((text_x, text_y), line, fill=self.HEADER_COLOR, font=fonts["name"])
            text_y += self.LINE_HEIGHTS["name"]

        # 时间（灰色）
        if content["time_lines"]:
            text_y += self.NAME_TIME_GAP
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

    def _draw_repost(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, content: dict, y_pos: int, card_width: int, fonts: dict
    ) -> int:
        """绘制转发内容"""
        # 计算转发区域位置
        repost_x = self.PADDING
        repost_y = y_pos
        repost_width = card_width - 2 * self.PADDING
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

        # 转发内容区域
        content_x = repost_x + self.REPOST_PADDING
        content_y = repost_y + self.REPOST_PADDING
        content_width = content["content_width"]
        current_y = content_y

        # 绘制转发头部（头像和用户名）
        if content["avatar"] or content["name_lines"]:
            current_y = self._draw_repost_header(image, draw, content, content_x, current_y, fonts)

        # 绘制转发文本
        if content["text_lines"]:
            current_y += 8  # 间距
            current_y = self._draw_repost_text(draw, content["text_lines"], content_x, current_y, fonts)

        # 绘制转发媒体
        if content["media_items"]:
            current_y += 8  # 间距
            current_y = self._draw_repost_media(image, content["media_items"], content_x, current_y, content_width)

        return y_pos + repost_height + self.SECTION_SPACING

    def _draw_repost_header(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, content: dict, x_pos: int, y_pos: int, fonts: dict
    ) -> int:
        """绘制转发头部"""
        # 绘制头像
        avatar = content["avatar"] if content["avatar"] else self._create_repost_avatar_placeholder()
        image.paste(avatar, (x_pos, y_pos), avatar)

        # 绘制用户名和时间
        text_x = x_pos + self.REPOST_AVATAR_SIZE + self.REPOST_AVATAR_GAP
        text_y = y_pos

        # 用户名
        for line in content["name_lines"]:
            draw.text((text_x, text_y), line, fill=self.TEXT_COLOR, font=fonts["repost_name"])
            text_y += self.REPOST_LINE_HEIGHTS["repost_name"]

        # 时间
        if content["time_lines"]:
            text_y += 4  # 用户名和时间间距
            for line in content["time_lines"]:
                draw.text((text_x, text_y), line, fill=self.EXTRA_COLOR, font=fonts["repost_time"])
                text_y += self.REPOST_LINE_HEIGHTS["repost_time"]

        return y_pos + max(self.REPOST_AVATAR_SIZE, text_y - y_pos)

    def _draw_repost_text(
        self, draw: ImageDraw.ImageDraw, lines: list[str], x_pos: int, y_pos: int, fonts: dict
    ) -> int:
        """绘制转发文本"""
        current_y = y_pos
        for line in lines:
            draw.text((x_pos, current_y), line, fill=self.TEXT_COLOR, font=fonts["repost_text"])
            current_y += self.REPOST_LINE_HEIGHTS["repost_text"]
        return current_y

    def _draw_repost_media(
        self, image: Image.Image, media_items: list[Image.Image], x_pos: int, y_pos: int, content_width: int
    ) -> int:
        """绘制转发媒体（图片网格）"""
        if not media_items:
            return y_pos

        # 计算网格布局
        cols = min(3, len(media_items))
        rows = (len(media_items) + cols - 1) // cols

        # 计算每个图片的尺寸
        max_img_size = min(200, content_width // 3)
        img_spacing = 4

        current_y = y_pos

        for row in range(rows):
            row_start = row * cols
            row_end = min(row_start + cols, len(media_items))
            row_items = media_items[row_start:row_end]

            # 计算这一行的最大高度
            max_height = max(img.height for img in row_items)

            # 绘制这一行的图片
            for i, img in enumerate(row_items):
                img_x = x_pos + i * (max_img_size + img_spacing)
                img_y = current_y

                # 居中放置图片
                y_offset = (max_height - img.height) // 2
                image.paste(img, (img_x, img_y + y_offset))

            current_y += max_height + img_spacing

        return current_y

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

    @classmethod
    def load_custom_fonts(cls):
        """加载字体"""
        font_path = Path(__file__).parent / "fonts" / "HYSongYunLangHeiW-1.ttf"
        # 加载主字体
        main_fonts = {name: ImageFont.truetype(font_path, size) for name, size in cls.FONT_SIZES.items()}
        # 加载转发字体
        repost_fonts = {name: ImageFont.truetype(font_path, size) for name, size in cls.REPOST_FONT_SIZES.items()}
        # 合并字体字典
        cls.FONTS = {**main_fonts, **repost_fonts}
