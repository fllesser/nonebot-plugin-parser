from io import BytesIO
from typing import TypeVar, ClassVar, ParamSpec
from pathlib import Path
from functools import wraps, lru_cache
from dataclasses import dataclass
from collections.abc import Callable, Awaitable
from typing_extensions import override

import emoji
from PIL import Image, ImageDraw, ImageFont
from nonebot import logger
from apilmoji import Apilmoji, EmojiCDNSource
from apilmoji.core import get_font_height

from .base import ParseResult, ImageRenderer
from ..config import pconfig
from ..parsers import GraphicsContent

# 定义类型变量
P = ParamSpec("P")
T = TypeVar("T")

Color = tuple[int, int, int]
PILImage = Image.Image
PILImageDraw = ImageDraw.ImageDraw

try:
    import emosvg
except ImportError:
    emosvg = None


def suppress_exception(
    func: Callable[P, T],
) -> Callable[P, T | None]:
    """装饰器：捕获所有异常并返回 None"""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"函数 {func.__name__} 执行失败: {e}")
            return None

    return wrapper


def suppress_exception_async(
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T | None]]:
    """装饰器：捕获所有异常并返回 None"""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"函数 {func.__name__} 执行失败: {e}")
            return None

    return wrapper


@dataclass(eq=False, frozen=True, slots=True)
class FontInfo:
    """字体信息数据类"""

    font: ImageFont.FreeTypeFont
    fill: Color
    line_height: int
    cjk_width: int

    def __hash__(self) -> int:
        """实现哈希方法以支持 @lru_cache"""
        return hash((id(self.font), self.line_height, self.cjk_width, self.fill))

    @lru_cache(maxsize=400)
    def get_char_width(self, char: str) -> int:
        """获取字符宽度，使用缓存优化"""
        return int(self.font.getlength(char, direction="ltr"))

    def get_char_width_fast(self, char: str) -> int:
        """快速获取单个字符宽度"""
        if "\u4e00" <= char <= "\u9fff":
            return self.cjk_width
        else:
            return self.get_char_width(char)

    def get_text_width(self, text: str) -> int:
        """计算文本宽度，使用预计算的字符宽度优化性能

        Args:
            text: 要计算宽度的文本

        Returns:
            文本宽度（像素）
        """
        if not text:
            return 0

        total_width = 0
        for char in text:
            total_width += self.get_char_width_fast(char)
        return total_width


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
    """字体信息"""

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
            font_infos[name] = FontInfo(
                font=font,
                fill=fill,
                line_height=height,
                cjk_width=size,
            )
        return FontSet(**font_infos)


@dataclass(eq=False, frozen=True, slots=True)
class SectionData:
    """基础部分数据类"""

    height: int


@dataclass(eq=False, frozen=True, slots=True)
class HeaderSectionData(SectionData):
    """Header 部分数据"""

    avatar: PILImage | None
    name: str
    time: str | None
    text_height: int


@dataclass(eq=False, frozen=True, slots=True)
class TitleSectionData(SectionData):
    """标题部分数据"""

    lines: list[str]


@dataclass(eq=False, frozen=True, slots=True)
class CoverSectionData(SectionData):
    """封面部分数据"""

    cover_img: PILImage


@dataclass(eq=False, frozen=True, slots=True)
class TextSectionData(SectionData):
    """文本部分数据"""

    lines: list[str]


@dataclass(eq=False, frozen=True, slots=True)
class ExtraSectionData(SectionData):
    """额外信息部分数据"""

    lines: list[str]


@dataclass(eq=False, frozen=True, slots=True)
class RepostSectionData(SectionData):
    """转发部分数据"""

    scaled_image: PILImage


@dataclass(eq=False, frozen=True, slots=True)
class ImageGridSectionData(SectionData):
    """图片网格部分数据"""

    images: list[PILImage]
    cols: int
    rows: int
    has_more: bool
    remaining_count: int


@dataclass(eq=False, frozen=True, slots=True)
class GraphicsSectionData(SectionData):
    """图文内容部分数据"""

    text_lines: list[str]
    image: PILImage
    alt_text: str | None = None


@dataclass
class RenderContext:
    """渲染上下文，存储渲染过程中的状态信息"""

    result: ParseResult
    """解析结果"""
    card_width: int
    """卡片宽度"""
    content_width: int
    """内容宽度"""
    image: PILImage
    """当前图像"""
    draw: PILImageDraw
    """绘图对象"""
    not_repost: bool = True
    """是否为非转发内容"""
    y_pos: int = 0
    """当前绘制位置（绘制阶段使用）"""


class CommonRenderer(ImageRenderer):
    """统一的渲染器，将解析结果转换为消息"""

    # 卡片配置常量
    PADDING = 25
    """内边距"""
    AVATAR_SIZE = 80
    """头像大小"""
    AVATAR_TEXT_GAP = 15
    """头像和文字之间的间距"""
    MAX_COVER_WIDTH = 1000
    """封面最大宽度"""
    MAX_COVER_HEIGHT = 800
    """封面最大高度"""
    DEFAULT_CARD_WIDTH = 800
    """默认卡片宽度"""
    MIN_CARD_WIDTH = 400
    """最小卡片宽度"""
    SECTION_SPACING = 15
    """部分间距"""
    NAME_TIME_GAP = 5
    """名称和时间之间的间距"""
    AVATAR_UPSCALE_FACTOR = 2
    """头像圆形框超采样倍数"""

    # 图片处理配置
    MIN_COVER_WIDTH = 300
    """最小封面宽度"""
    MIN_COVER_HEIGHT = 200
    """最小封面高度"""
    MAX_IMAGE_HEIGHT = 800
    """图片最大高度限制"""
    IMAGE_3_GRID_SIZE = 300
    """图片3列网格最大尺寸"""
    IMAGE_2_GRID_SIZE = 400
    """图片2列网格最大尺寸"""
    IMAGE_GRID_SPACING = 4
    """图片网格间距"""
    MAX_IMAGES_DISPLAY = 9
    """最大显示图片数量"""
    IMAGE_GRID_COLS = 3
    """图片网格列数"""

    # 转发内容配置
    REPOST_PADDING = 12
    """转发内容内边距"""
    REPOST_SCALE = 0.88
    """转发缩放比例"""

    # 资源名称
    _EMOJIS = "emojis"
    _RESOURCES = "resources"
    _BUTTON_FILENAME = "media_button.png"
    _FONT_FILENAME = "HYSongYunLangHeiW-1.ttf"

    # 颜色配置
    BG_COLOR: ClassVar[Color] = (255, 255, 255)
    """背景色"""
    REPOST_BG_COLOR: ClassVar[Color] = (247, 247, 247)
    """转发背景色"""
    REPOST_BORDER_COLOR: ClassVar[Color] = (230, 230, 230)
    """转发边框色"""

    # 路径配置
    RESOURCES_DIR: ClassVar[Path] = Path(__file__).parent / _RESOURCES
    """资源目录"""
    DEFAULT_FONT_PATH: ClassVar[Path] = RESOURCES_DIR / _FONT_FILENAME
    """默认字体路径"""
    DEFAULT_VIDEO_BUTTON_PATH: ClassVar[Path] = RESOURCES_DIR / _BUTTON_FILENAME
    """默认视频按钮路径"""
    EMOJI_SOURCE: ClassVar[EmojiCDNSource] = EmojiCDNSource(
        base_url=pconfig.emoji_cdn,
        style=pconfig.emoji_style,
        cache_dir=pconfig.cache_dir / _EMOJIS,
        enable_tqdm=True,
    )
    """Emoji Source"""

    @classmethod
    def load_resources(cls):
        """加载资源"""
        cls._load_fonts()
        cls._load_video_button()
        cls._load_platform_logos()

    @classmethod
    def _load_fonts(cls):
        """预加载自定义字体"""

        font_path = pconfig.custom_font or cls.DEFAULT_FONT_PATH
        # 创建 FontSet 对象
        cls.fontset = FontSet.new(font_path)
        logger.success(f"加载字体「{font_path.name}」成功")

    @classmethod
    def _load_video_button(cls):
        """预加载视频按钮"""
        with Image.open(cls.DEFAULT_VIDEO_BUTTON_PATH) as img:
            cls.video_button_image: PILImage = img.convert("RGBA")

        # 设置透明度为 30%
        alpha = cls.video_button_image.split()[-1]  # 获取 alpha 通道
        alpha = alpha.point(lambda x: int(x * 0.3))  # 将透明度设置为 30%
        cls.video_button_image.putalpha(alpha)

    @classmethod
    def _load_platform_logos(cls):
        """预加载平台 logo"""
        from ..constants import PlatformEnum

        cls.platform_logos: dict[str, PILImage] = {}
        for platform_name in PlatformEnum:
            logo_path = cls.RESOURCES_DIR / f"{platform_name}.png"
            if logo_path.exists():
                with Image.open(logo_path) as img:
                    cls.platform_logos[str(platform_name)] = img.convert("RGBA")

    @classmethod
    async def text(
        cls,
        ctx: RenderContext,
        xy: tuple[int, int],
        lines: list[str],
        font: FontInfo,
    ) -> int:
        """绘制文本"""
        if emosvg is not None:
            emosvg.text(ctx.image, xy, lines, font.font, fill=font.fill, line_height=font.line_height)
        else:
            await Apilmoji.text(
                ctx.image, xy, lines, font.font, fill=font.fill, line_height=font.line_height, source=cls.EMOJI_SOURCE
            )
        return font.line_height * len(lines)

    @staticmethod
    def text_single_line(
        ctx: RenderContext,
        xy: tuple[int, int],
        line: str,
        font: FontInfo,
    ) -> int:
        """绘制单行文本"""
        ctx.draw.text(xy, line, font=font.font, fill=font.fill)
        return font.line_height

    @override
    async def render_image(self, result: ParseResult) -> bytes:
        """使用 PIL 绘制通用社交媒体帖子卡片

        Args:
            result: 解析结果

        Returns:
            PNG 图片的字节数据，如果没有足够的内容则返回 None
        """
        # 调用内部方法生成图片
        image = await self._create_card_image(result)

        # 将图片转换为字节
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    async def _create_card_image(
        self,
        result: ParseResult,
        not_repost: bool = True,
    ) -> PILImage:
        """创建卡片图片（内部方法，用于递归调用）

        Args:
            result: 解析结果
            not_repost: 是否为非转发内容，转发内容为 False

        Returns:
            PIL Image 对象
        """
        # 计算必要参数
        card_width = self.DEFAULT_CARD_WIDTH
        content_width = card_width - 2 * self.PADDING

        # 计算各部分内容的高度
        sections = await self._calculate_sections(result, content_width)

        # 计算总高度
        card_height = sum(section.height for section in sections)
        card_height += self.PADDING * 2 + self.SECTION_SPACING * (len(sections) - 1)

        # 创建画布
        bg_color = self.BG_COLOR if not_repost else self.REPOST_BG_COLOR
        image = Image.new(
            "RGB",
            (card_width, card_height),
            bg_color,
        )

        # 创建完整的渲染上下文
        ctx = RenderContext(
            result=result,
            card_width=card_width,
            content_width=content_width,
            image=image,
            draw=ImageDraw.Draw(image),
            not_repost=not_repost,
            y_pos=self.PADDING,  # 以 padding 作为起始
        )
        # 绘制各部分内容
        await self._draw_sections(ctx, sections)
        return image

    @suppress_exception
    def _load_and_resize_cover(
        self,
        cover_path: Path | None,
        content_width: int,
    ) -> PILImage | None:
        """加载并调整封面尺寸

        Args:
            cover_path: 封面路径
            content_width: 内容区域宽度, 封面会缩放到此宽度以确保左右padding一致
        """
        if not cover_path or not cover_path.exists():
            return None

        with Image.open(cover_path) as original_img:
            # 转换为 RGB 模式以确保兼容性
            if original_img.mode not in ("RGB", "RGBA"):
                cover_img = original_img.convert("RGB")
            else:
                cover_img = original_img

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

                cover_img = cover_img.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS,
                )
            elif cover_img is original_img:
                # 如果没有做任何转换，需要 copy 一份，因为原图会在 with 结束时关闭
                cover_img = cover_img.copy()

            return cover_img

    @suppress_exception
    def _load_and_process_avatar(self, avatar: Path | None) -> PILImage | None:
        """加载并处理头像（圆形裁剪，带抗锯齿）"""
        if not avatar or not avatar.exists():
            return None

        with Image.open(avatar) as original_img:
            # 转换为 RGBA 模式（用于更好的抗锯齿效果）
            if original_img.mode != "RGBA":
                avatar_img = original_img.convert("RGBA")
            else:
                avatar_img = original_img

            # 使用超采样技术提高质量：先放大到指定倍数
            scale = self.AVATAR_UPSCALE_FACTOR
            temp_size = self.AVATAR_SIZE * scale
            avatar_img = avatar_img.resize(
                (temp_size, temp_size),
                Image.Resampling.LANCZOS,
            )

            # 创建高分辨率圆形遮罩（带抗锯齿）
            mask = Image.new("L", (temp_size, temp_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, temp_size - 1, temp_size - 1), fill=255)

            # 应用遮罩
            output_avatar = Image.new(
                "RGBA",
                (temp_size, temp_size),
                (0, 0, 0, 0),
            )
            output_avatar.paste(avatar_img, (0, 0))
            output_avatar.putalpha(mask)

            # 缩小到目标尺寸（抗锯齿缩放）
            output_avatar = output_avatar.resize(
                (self.AVATAR_SIZE, self.AVATAR_SIZE),
                Image.Resampling.LANCZOS,
            )

            return output_avatar

    async def _calculate_sections(self, result: ParseResult, content_width: int) -> list[SectionData]:
        """计算各部分内容的高度和数据"""
        sections: list[SectionData] = []

        # 1. Header 部分
        header_section = await self._calculate_header_section(result)
        if header_section is not None:
            sections.append(header_section)

        # 2. 标题部分
        if result.title:
            title_lines = self._wrap_text(
                result.title,
                content_width,
                self.fontset.title,
            )
            title_height = len(title_lines) * self.fontset.title.line_height
            sections.append(TitleSectionData(height=title_height, lines=title_lines))

        # 3. 封面，图集，图文内容
        if cover_img := self._load_and_resize_cover(
            await result.cover_path,
            content_width=content_width,
        ):
            sections.append(CoverSectionData(height=cover_img.height, cover_img=cover_img))
        elif result.img_contents:
            # 如果没有封面但有图片，处理图片列表
            img_grid_section = await self._calculate_image_grid_section(
                result,
                content_width,
            )
            if img_grid_section:
                sections.append(img_grid_section)
        elif result.graphics_contents:
            for graphics_content in result.graphics_contents:
                graphics_section = await self._calculate_graphics_section(
                    graphics_content,
                    content_width,
                )
                if graphics_section:
                    sections.append(graphics_section)

        # 5. 文本内容
        if result.text:
            text_lines = self._wrap_text(
                result.text,
                content_width,
                self.fontset.text,
            )
            text_height = len(text_lines) * self.fontset.text.line_height
            sections.append(TextSectionData(height=text_height, lines=text_lines))

        # 6. 额外信息
        if result.extra_info:
            extra_lines = self._wrap_text(
                result.extra_info,
                content_width,
                self.fontset.extra,
            )
            extra_height = len(extra_lines) * self.fontset.extra.line_height
            sections.append(ExtraSectionData(height=extra_height, lines=extra_lines))

        # 7. 转发内容
        if result.repost:
            repost_section = await self._calculate_repost_section(result.repost)
            sections.append(repost_section)

        return sections

    @suppress_exception_async
    async def _calculate_graphics_section(
        self, graphics_content: GraphicsContent, content_width: int
    ) -> GraphicsSectionData | None:
        """计算图文内容部分的高度和内容"""
        # 加载图片
        img_path = await graphics_content.get_path()
        with Image.open(img_path) as original_img:
            # 调整图片尺寸以适应内容宽度
            if original_img.width > content_width:
                ratio = content_width / original_img.width
                new_height = int(original_img.height * ratio)
                image = original_img.resize(
                    (content_width, new_height),
                    Image.Resampling.LANCZOS,
                )
            else:
                # 如果不需要缩放，copy 一份
                image = original_img.copy()

            # 处理文本内容
            text_lines = []
            if graphics_content.text:
                text_lines = self._wrap_text(
                    graphics_content.text,
                    content_width,
                    self.fontset.text,
                )

            # 计算总高度：文本高度 + 图片高度 + alt文本高度 + 间距
            text_height = len(text_lines) * self.fontset.text.line_height if text_lines else 0
            alt_height = self.fontset.extra.line_height if graphics_content.alt else 0
            total_height = text_height + image.height + alt_height
            if text_lines:
                total_height += self.SECTION_SPACING  # 文本和图片之间的间距
            if graphics_content.alt:
                total_height += self.SECTION_SPACING  # 图片和alt文本之间的间距

            return GraphicsSectionData(
                height=total_height,
                text_lines=text_lines,
                image=image,
                alt_text=graphics_content.alt,
            )

    async def _calculate_header_section(
        self,
        result: ParseResult,
    ) -> HeaderSectionData | None:
        """计算 header 部分的高度和内容"""
        if result.author is None:
            return None

        # 加载头像
        avatar_img = self._load_and_process_avatar(await result.author.get_avatar_path())

        text_height = self.fontset.name.line_height
        time = result.formartted_datetime
        if time:
            text_height += self.NAME_TIME_GAP + self.fontset.extra.line_height

        header_height = max(self.AVATAR_SIZE, text_height)

        return HeaderSectionData(
            height=header_height,
            avatar=avatar_img,
            name=result.author.name,
            time=result.formartted_datetime,
            text_height=text_height,
        )

    async def _calculate_repost_section(self, repost: ParseResult) -> RepostSectionData:
        """计算转发内容的高度和内容（递归调用绘制方法）"""
        repost_image = await self._create_card_image(repost, False)
        # 缩放图片
        scaled_width = int(repost_image.width * self.REPOST_SCALE)
        scaled_height = int(repost_image.height * self.REPOST_SCALE)
        repost_image_scaled = repost_image.resize(
            (scaled_width, scaled_height),
            Image.Resampling.LANCZOS,
        )

        return RepostSectionData(
            height=scaled_height + self.REPOST_PADDING * 2,  # 加上转发容器的内边距
            scaled_image=repost_image_scaled,
        )

    async def _calculate_image_grid_section(
        self, result: ParseResult, content_width: int
    ) -> ImageGridSectionData | None:
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
        img_count = len(img_contents)

        for img_content in img_contents:
            img_path = await img_content.get_path()
            # 使用装饰器保护的方法，失败会返回 None
            img = await self._load_and_process_grid_image(img_path, content_width, img_count)
            if img is not None:
                processed_images.append(img)

        if not processed_images:
            return None

        # 计算网格布局
        image_count = len(processed_images)

        if image_count == 1:
            # 单张图片
            cols, rows = 1, 1
        elif image_count in (2, 4):
            # 2张或4张图片，使用2列布局
            cols, rows = 2, (image_count + 1) // 2
        else:
            # 多张图片，使用3列布局（九宫格）
            cols = self.IMAGE_GRID_COLS
            rows = (image_count + cols - 1) // cols

        # 计算高度
        max_img_height = max(img.height for img in processed_images)
        if len(processed_images) == 1:
            # 单张图片
            grid_height = max_img_height
        else:
            # 多张图片：上间距 + (图片 + 间距) * 行数
            grid_height = self.IMAGE_GRID_SPACING + rows * (max_img_height + self.IMAGE_GRID_SPACING)

        return ImageGridSectionData(
            height=grid_height,
            images=processed_images,
            cols=cols,
            rows=rows,
            has_more=has_more,
            remaining_count=remaining_count,
        )

    @suppress_exception_async
    async def _load_and_process_grid_image(
        self,
        img_path: Path,
        content_width: int,
        img_count: int,
    ) -> PILImage | None:
        """加载并处理网格图片

        Args:
            img_path: 图片路径
            content_width: 内容宽度
            img_count: 图片总数（用于决定处理方式）

        Returns:
            处理后的图片对象，失败返回 None
        """
        if not img_path.exists():
            return None

        with Image.open(img_path) as original_img:
            img = original_img

            # 根据图片数量决定处理方式
            if img_count >= 2:
                # 2张及以上图片，统一为方形
                img = self._crop_to_square(img)

            # 计算图片尺寸
            if img_count == 1:
                # 单张图片，根据卡片宽度调整，与视频封面保持一致
                max_width = content_width
                max_height = min(self.MAX_IMAGE_HEIGHT, content_width)  # 限制最大高度
                if img.width > max_width or img.height > max_height:
                    ratio = min(max_width / img.width, max_height / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                elif img is original_img:
                    # 如果没有做任何转换，需要 copy 一份
                    img = img.copy()
            else:
                # 多张图片，计算最大尺寸
                if img_count in (2, 4):
                    # 2张或4张图片，使用2列布局
                    num_gaps = 3  # 2列有3个间距
                    max_size = (content_width - self.IMAGE_GRID_SPACING * num_gaps) // 2
                    max_size = min(max_size, self.IMAGE_2_GRID_SIZE)
                else:
                    # 多张图片，使用3列布局
                    num_gaps = self.IMAGE_GRID_COLS + 1
                    max_size = (content_width - self.IMAGE_GRID_SPACING * num_gaps) // self.IMAGE_GRID_COLS
                    max_size = min(max_size, self.IMAGE_3_GRID_SIZE)

                # 调整多张图片的尺寸
                if img.width > max_size or img.height > max_size:
                    ratio = min(max_size / img.width, max_size / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                elif img is original_img:
                    # 如果没有做任何转换，需要 copy 一份
                    img = img.copy()

            return img

    def _crop_to_square(self, img: PILImage) -> PILImage:
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

    async def _draw_sections(self, ctx: RenderContext, sections: list[SectionData]) -> None:
        """绘制所有内容到画布上"""
        for section in sections:
            match section:
                case HeaderSectionData() as header:
                    await self._draw_header(ctx, header)
                case TitleSectionData() as title:
                    await self._draw_title(ctx, title.lines)
                case CoverSectionData() as cover:
                    self._draw_cover(ctx, cover.cover_img)
                case TextSectionData() as text:
                    await self._draw_text(ctx, text.lines)
                case GraphicsSectionData() as graphics:
                    await self._draw_graphics(ctx, graphics)
                case ExtraSectionData() as extra:
                    await self._draw_extra(ctx, extra.lines)
                case RepostSectionData() as repost:
                    self._draw_repost(ctx, repost)
                case ImageGridSectionData() as image_grid:
                    self._draw_image_grid(ctx, image_grid)

    def _create_avatar_placeholder(self) -> PILImage:
        """创建默认头像占位符"""
        # 头像占位符配置常量
        placeholder_bg_color = (230, 230, 230, 255)
        placeholder_fg_color = (200, 200, 200, 255)
        head_ratio = 0.35  # 头部位置比例
        head_radius_ratio = 1 / 6  # 头部半径比例
        shoulder_y_ratio = 0.55  # 肩部 Y 位置比例
        shoulder_width_ratio = 0.55  # 肩部宽度比例
        shoulder_height_ratio = 0.6  # 肩部高度比例

        placeholder = Image.new(
            "RGBA",
            (self.AVATAR_SIZE, self.AVATAR_SIZE),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(placeholder)

        # 绘制圆形背景
        draw.ellipse(
            (0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1),
            fill=placeholder_bg_color,
        )

        # 绘制简单的用户图标（圆形头部 + 肩部）
        center_x = self.AVATAR_SIZE // 2

        # 头部圆形
        head_radius = int(self.AVATAR_SIZE * head_radius_ratio)
        head_y = int(self.AVATAR_SIZE * head_ratio)
        draw.ellipse(
            (
                center_x - head_radius,
                head_y - head_radius,
                center_x + head_radius,
                head_y + head_radius,
            ),
            fill=placeholder_fg_color,
        )

        # 肩部
        shoulder_y = int(self.AVATAR_SIZE * shoulder_y_ratio)
        shoulder_width = int(self.AVATAR_SIZE * shoulder_width_ratio)
        shoulder_height = int(self.AVATAR_SIZE * shoulder_height_ratio)
        draw.ellipse(
            (
                center_x - shoulder_width // 2,
                shoulder_y,
                center_x + shoulder_width // 2,
                shoulder_y + shoulder_height,
            ),
            fill=placeholder_fg_color,
        )

        # 创建圆形遮罩确保不超出边界
        mask = Image.new("L", (self.AVATAR_SIZE, self.AVATAR_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, self.AVATAR_SIZE - 1, self.AVATAR_SIZE - 1), fill=255)

        # 应用遮罩
        placeholder.putalpha(mask)
        return placeholder

    async def _draw_header(self, ctx: RenderContext, section: HeaderSectionData) -> None:
        """绘制 header 部分"""
        x_pos = self.PADDING

        # 绘制头像或占位符
        avatar = section.avatar if section.avatar else self._create_avatar_placeholder()
        ctx.image.paste(avatar, (x_pos, ctx.y_pos), avatar)

        # 文字始终从头像位置后面开始
        text_x = self.PADDING + self.AVATAR_SIZE + self.AVATAR_TEXT_GAP

        # 计算文字垂直居中位置（对齐头像中轴）
        avatar_center = ctx.y_pos + self.AVATAR_SIZE // 2
        text_start_y = avatar_center - section.text_height // 2
        text_y = text_start_y

        # 发布者名称（蓝色）
        text_y += self.text_single_line(
            ctx,
            (text_x, text_y),
            section.name,
            font=self.fontset.name,
        )

        # 时间（灰色）
        if section.time:
            text_y += self.NAME_TIME_GAP
            text_y += self.text_single_line(
                ctx,
                (text_x, text_y),
                section.time,
                font=self.fontset.extra,
            )

        # 在右侧绘制平台 logo（仅在非转发内容时绘制）
        if ctx.not_repost:
            platform_name = ctx.result.platform.name
            if platform_name in self.platform_logos:
                logo_img = self.platform_logos[platform_name]
                # 计算 logo 位置（右侧对齐）
                logo_x = ctx.image.width - self.PADDING - logo_img.width
                # 垂直居中对齐头像
                logo_y = ctx.y_pos + (self.AVATAR_SIZE - logo_img.height) // 2
                ctx.image.paste(logo_img, (logo_x, logo_y), logo_img)

        ctx.y_pos += section.height + self.SECTION_SPACING

    async def _draw_title(self, ctx: RenderContext, lines: list[str]) -> None:
        """绘制标题"""
        ctx.y_pos += await self.text(
            ctx,
            (self.PADDING, ctx.y_pos),
            lines,
            self.fontset.title,
        )

        ctx.y_pos += self.SECTION_SPACING

    def _draw_cover(self, ctx: RenderContext, cover_img: PILImage) -> None:
        """绘制封面"""
        # 封面从左边padding开始，和文字、头像对齐
        x_pos = self.PADDING
        ctx.image.paste(cover_img, (x_pos, ctx.y_pos))

        # 添加视频播放按钮（居中）
        button_size = 128  # 固定使用 128x128 尺寸
        button_x = x_pos + (cover_img.width - button_size) // 2
        button_y = ctx.y_pos + (cover_img.height - button_size) // 2
        ctx.image.paste(
            self.video_button_image,
            (button_x, button_y),
            self.video_button_image,
        )

        ctx.y_pos += cover_img.height + self.SECTION_SPACING

    async def _draw_text(self, ctx: RenderContext, lines: list[str]) -> None:
        """绘制文本内容"""
        ctx.y_pos += await self.text(
            ctx,
            (self.PADDING, ctx.y_pos),
            lines,
            self.fontset.text,
        )
        ctx.y_pos += self.SECTION_SPACING

    async def _draw_graphics(self, ctx: RenderContext, section: GraphicsSectionData) -> None:
        """绘制图文内容"""
        # 绘制文本内容（如果有）
        if section.text_lines:
            ctx.y_pos += await self.text(
                ctx,
                (self.PADDING, ctx.y_pos),
                section.text_lines,
                self.fontset.text,
            )
            ctx.y_pos += self.SECTION_SPACING  # 文本和图片之间的间距

        # 绘制图片（居中）
        x_pos = self.PADDING + (ctx.content_width - section.image.width) // 2
        ctx.image.paste(section.image, (x_pos, ctx.y_pos))
        ctx.y_pos += section.image.height

        # 绘制 alt 文本（如果有，居中显示）
        if section.alt_text:
            ctx.y_pos += self.SECTION_SPACING  # 图片和alt文本之间的间距
            # 计算文本居中位置
            extra_font_info = self.fontset.extra
            text_width = extra_font_info.get_text_width(section.alt_text)
            text_x = self.PADDING + (ctx.content_width - text_width) // 2
            ctx.y_pos += self.text_single_line(
                ctx,
                (text_x, ctx.y_pos),
                section.alt_text,
                self.fontset.extra,
            )

        ctx.y_pos += self.SECTION_SPACING

    async def _draw_extra(self, ctx: RenderContext, lines: list[str]) -> None:
        """绘制额外信息"""
        ctx.y_pos += await self.text(
            ctx,
            (self.PADDING, ctx.y_pos),
            lines,
            self.fontset.extra,
        )

    def _draw_repost(self, ctx: RenderContext, section: RepostSectionData) -> None:
        """绘制转发内容"""
        # 获取缩放后的转发图片
        repost_image = section.scaled_image

        # 转发框占满整个内容区域，左右和边缘对齐
        repost_x = self.PADDING
        repost_y = ctx.y_pos
        repost_width = ctx.content_width  # 转发框宽度等于内容区域宽度
        repost_height = section.height

        # 绘制转发背景（圆角矩形）
        self._draw_rounded_rectangle(
            ctx.image,
            (repost_x, repost_y, repost_x + repost_width, repost_y + repost_height),
            self.REPOST_BG_COLOR,
            radius=8,
        )

        # 绘制转发边框
        self._draw_rounded_rectangle_border(
            ctx.draw,
            (repost_x, repost_y, repost_x + repost_width, repost_y + repost_height),
            self.REPOST_BORDER_COLOR,
            radius=8,
            width=1,
        )

        # 转发图片在转发容器中居中
        card_x = repost_x + (repost_width - repost_image.width) // 2
        card_y = repost_y + self.REPOST_PADDING

        # 将缩放后的转发图片贴到主画布上
        ctx.image.paste(repost_image, (card_x, card_y))

        ctx.y_pos += repost_height + self.SECTION_SPACING

    def _draw_image_grid(self, ctx: RenderContext, section: ImageGridSectionData) -> None:
        """绘制图片网格"""
        images = section.images
        cols = section.cols
        rows = section.rows
        has_more = section.has_more
        remaining_count = section.remaining_count

        if not images:
            return

        # 计算每个图片的尺寸和间距
        available_width = ctx.content_width  # 可用宽度
        img_spacing = self.IMAGE_GRID_SPACING

        # 根据图片数量计算每个图片的尺寸
        if len(images) == 1:
            # 单张图片，使用完整的可用宽度，与视频封面保持一致
            max_img_size = available_width
        else:
            # 多张图片，统一使用间距计算，确保所有间距相同
            num_gaps = cols + 1  # 2列有3个间距，3列有4个间距
            calculated_size = (available_width - img_spacing * num_gaps) // cols
            max_img_size = self.IMAGE_2_GRID_SIZE if cols == 2 else self.IMAGE_3_GRID_SIZE
            max_img_size = min(calculated_size, max_img_size)

        current_y = ctx.y_pos

        for row in range(rows):
            row_start = row * cols
            row_end = min(row_start + cols, len(images))
            row_images = images[row_start:row_end]

            # 计算这一行的最大高度
            max_height = max(img.height for img in row_images)

            # 绘制这一行的图片
            for i, img in enumerate(row_images):
                # 统一使用间距计算方式
                img_x = self.PADDING + img_spacing + i * (max_img_size + img_spacing)

                img_y = current_y + img_spacing  # 每行上方都有间距

                # 居中放置图片
                y_offset = (max_height - img.height) // 2
                ctx.image.paste(img, (img_x, img_y + y_offset))

                # 如果是最后一张图片且有更多图片，绘制+N效果
                if has_more and row == rows - 1 and i == len(row_images) - 1 and len(images) == self.MAX_IMAGES_DISPLAY:
                    self._draw_more_indicator(
                        ctx.image,
                        img_x,
                        img_y,
                        max_img_size,
                        max_height,
                        remaining_count,
                    )

            current_y += img_spacing + max_height

        ctx.y_pos = current_y + img_spacing + self.SECTION_SPACING

    def _draw_more_indicator(
        self,
        image: PILImage,
        img_x: int,
        img_y: int,
        img_width: int,
        img_height: int,
        count: int,
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
        text = "+" + str(count)
        indicator_font = self.fontset.indicator
        # 计算文字位置（居中）
        text_width = indicator_font.get_text_width(text)
        text_x = img_x + (img_width - text_width) // 2
        text_y = img_y + (img_height - indicator_font.line_height) // 2

        # 绘制50%透明白色文字
        draw.text((text_x, text_y), text, fill=indicator_font.fill, font=indicator_font.font)

    def _draw_rounded_rectangle(
        self,
        image: PILImage,
        bbox: tuple[int, int, int, int],
        fill_color: Color,
        radius: int = 8,
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
        draw: PILImageDraw,
        bbox: tuple[int, int, int, int],
        border_color: Color,
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

    def _wrap_text(self, text: str, max_width: int, font_info: FontInfo) -> list[str]:
        """使用 emoji.emoji_list 优化的文本自动换行算法，正确处理组合 emoji

        Args:
            text: 要处理的文本
            max_width: 最大宽度（像素）
            font_info: 字体信息对象

        Returns:
            换行后的文本列表
        """
        if not text:
            return []

        def is_punctuation(char: str) -> bool:
            """判断是否为不能为行首的标点符号"""
            return char in "，。！？；：、）】》〉」』〕〗〙〛…—·,.;:!?)]}"

        lines: list[str] = []
        paragraphs = text.splitlines()

        for paragraph in paragraphs:
            if not paragraph:
                lines.append("")
                continue

            # 使用 emoji.emoji_list 识别所有 emoji 组合
            emoji_list = emoji.emoji_list(paragraph)

            current_line = ""
            current_line_width = 0
            idx = 0  # 当前处理的字符索引

            while idx < len(paragraph):
                # 检查当前位置是否有 emoji, 包含组合 emoji
                for emoji_data in emoji_list:
                    if emoji_data["match_start"] == idx:
                        char = emoji_data["emoji"]
                        idx = emoji_data["match_end"]
                        char_width = font_info.font.size
                        break
                else:
                    # 处理普通字符
                    char = paragraph[idx]
                    idx += 1
                    char_width = font_info.get_char_width_fast(char)

                # 如果当前行为空，直接添加字符
                if not current_line:
                    current_line = char
                    current_line_width = char_width
                    continue

                # 如果是标点符号，直接添加到当前行（标点符号不应该单独成行）
                if len(char) == 1 and is_punctuation(char):
                    current_line += char
                    current_line_width += char_width
                    continue

                # 测试添加下一个字符后的宽度
                test_width = current_line_width + char_width

                if test_width <= max_width:
                    # 宽度合适，继续添加
                    current_line += char
                    current_line_width = test_width
                else:
                    # 宽度超限，需要断行
                    lines.append(current_line)
                    current_line = char
                    current_line_width = char_width

            # 保存最后一行
            if current_line:
                lines.append(current_line)

        return lines

    def _wrap_text_old(self, text: str, max_width: int, font_info: FontInfo) -> list[str]:
        """优化的文本自动换行算法，考虑中英文字符宽度相同

        Args:
            text: 要处理的文本
            max_width: 最大宽度（像素）
            font_info: 字体信息对象

        Returns:
            换行后的文本列表
        """
        if not text:
            return []

        def is_punctuation(char: str) -> bool:
            """判断是否为不能为行首的标点符号"""
            return char in "，。！？；：、）】》〉」』〕〗〙〛…—·,.;:!?)]}"

        lines: list[str] = []
        paragraphs = text.splitlines()

        for paragraph in paragraphs:
            if not paragraph:
                lines.append("")
                continue

            current_line = ""
            current_line_width = 0
            remaining_text = paragraph

            while remaining_text:
                next_char = remaining_text[0]
                char_width = font_info.get_char_width_fast(next_char)
                # 如果当前行为空，直接添加字符
                if not current_line:
                    current_line = next_char
                    current_line_width = char_width
                    remaining_text = remaining_text[1:]
                    continue

                # 如果是标点符号，直接添加到当前行（标点符号不应该单独成行）
                if is_punctuation(next_char):
                    current_line += next_char
                    current_line_width += char_width
                    remaining_text = remaining_text[1:]
                    continue

                # 测试添加下一个字符后的宽度
                test_width = current_line_width + char_width

                if test_width <= max_width:
                    # 宽度合适，继续添加
                    current_line += next_char
                    current_line_width = test_width
                    remaining_text = remaining_text[1:]
                else:
                    # 宽度超限，需要断行
                    lines.append(current_line)
                    current_line = next_char
                    current_line_width = char_width
                    remaining_text = remaining_text[1:]

            # 保存最后一行
            if current_line:
                lines.append(current_line)

        return lines
