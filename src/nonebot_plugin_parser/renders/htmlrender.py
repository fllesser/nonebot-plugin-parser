from __future__ import annotations

from dataclasses import field, dataclass
from typing_extensions import override

from nonebot import require

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import template_to_pic

from .base import ParseResult, ImageRenderer
from ..utils import fmt_duration
from .common import CommonRenderer
from ..config import pconfig


@dataclass(slots=True)
class CardPlatform:
    """卡片模板中的平台信息。

    Attributes:
        name: 平台标识名，如 ``bilibili``、``weibo``
        display_name: 用于展示的平台中文名
        logo_path: 平台 logo 的 file URI, 不存在时为 ``None``
    """

    name: str
    display_name: str
    logo_path: str | None = None


@dataclass(slots=True)
class CardAuthor:
    """卡片模板中的作者信息。

    Attributes:
        name: 作者名称
        avatar_path: 头像的 file URI，无头像时为 ``None``
    """

    name: str
    avatar_path: str | None = None


@dataclass(slots=True)
class CardVideoContent:
    """卡片模板中的单个视频内容。

    Attributes:
        cover_path: 视频封面的 file URI
        duration: 格式化后的时长字符串，如 ``"时长: 3:42"``
    """

    cover_path: str | None = None
    duration: str | None = None


@dataclass(slots=True)
class CardImageContent:
    """卡片模板中的单张图片。

    Attributes:
        path: 图片的 file URI
    """

    path: str


@dataclass(slots=True)
class CardGraphicsContent:
    """卡片模板中的图文混排内容。

    Attributes:
        path: 图片的 file URI
        text: 图片上方的文本
        alt: 图片描述（居中显示）
    """

    path: str
    text_before: str | None = None
    text_after: str | None = None
    alt: str | None = None


@dataclass(slots=True)
class CardData:
    """HTML 卡片渲染的完整模板数据。

    Jinja2 模板通过属性访问（如 ``result.title``）读取数据，
    与 ``dict`` 的中括号访问行为一致，无需修改模板。

    Attributes:
        title: 标题
        text: 正文内容
        formartted_datetime: 格式化后的发布时间
        extra_info: 额外信息文本
        platform: 平台信息
        author: 作者信息
        video_contents: 视频内容列表（封面 + 时长）
        cover_path: 首个视频封面的 file URI (兼容字段)
        img_contents: 图片内容列表
        graphics_contents: 图文内容列表
        content_type: 推断的内容类型标签 ("视频" / "图文" / "动态")
        play_icon_uri: 播放按钮图标的 file URI
        font_uri: 中文字体的 file URI
        repost: 转发内容（递归结构）
    """

    title: str | None = None
    text: str | None = None
    formartted_datetime: str | None = None
    extra_info: str | None = None
    platform: CardPlatform | None = None
    author: CardAuthor | None = None
    video_contents: list[CardVideoContent] = field(default_factory=list)
    cover_path: str | None = None
    img_contents: list[CardImageContent] = field(default_factory=list)
    graphics_contents: list[CardGraphicsContent] = field(default_factory=list)
    content_type: str | None = None
    play_icon_uri: str | None = None
    font_uri: str | None = None
    repost: CardData | None = None


class HtmlRenderer(ImageRenderer):
    """HTML 渲染器"""

    @override
    async def render_image(self, result: ParseResult) -> bytes:
        template_data = await self._resolve_parse_result(result)

        return await template_to_pic(
            template_path=str(self.templates_dir),
            template_name="card.html.jinja",
            templates={"result": template_data},
            pages={
                "viewport": {"width": 800, "height": 100},
                "base_url": f"file://{self.templates_dir}",
            },
        )

    async def _resolve_parse_result(self, result: ParseResult) -> CardData:
        """将 ``ParseResult`` 解析为模板可用的 ``CardData``，并等待异步资源路径。"""
        # 平台
        platform: CardPlatform | None = None
        if result.platform:
            logo_path = CommonRenderer.RESOURCES_DIR / f"{result.platform.name}.png"
            platform = CardPlatform(
                name=result.platform.name,
                display_name=result.platform.display_name,
                logo_path=logo_path.as_uri() if logo_path.exists() else None,
            )

        # 作者
        author: CardAuthor | None = None
        if result.author:
            avatar_path = await result.author.get_avatar_path()
            # 无头像时 fallback 到默认头像（与 CommonRenderer 保持一致）
            if not avatar_path:
                avatar_path = (
                    CommonRenderer.DEFAULT_AVATAR_PATH if CommonRenderer.DEFAULT_AVATAR_PATH.exists() else None
                )
            author = CardAuthor(
                name=result.author.name,
                avatar_path=avatar_path.as_uri() if avatar_path else None,
            )

        # 视频内容
        video_contents: list[CardVideoContent] = []
        for vc in result.video_contents:
            cover = await vc.get_cover_path()
            video_contents.append(
                CardVideoContent(
                    cover_path=cover.as_uri() if cover else None,
                    duration=vc.display_duration if vc.duration else None,
                )
            )

        cover_path = video_contents[0].cover_path if video_contents else None

        # 图片内容
        img_contents: list[CardImageContent] = []
        for img in result.img_contents:
            path = await img.get_path()
            img_contents.append(CardImageContent(path=path.as_uri()))

        # 动态视频标记：将首张图片提升为视频封面（播放按钮 + 时长）
        is_video = result.extra.get("is_video", False)
        if is_video and img_contents and not video_contents:
            promoted = img_contents.pop(0)
            duration_secs = result.extra.get("duration", 0)
            duration_str = None
            if duration_secs:
                duration_str = f"时长: {fmt_duration(duration_secs)}"
            video_contents.append(
                CardVideoContent(
                    cover_path=promoted.path,
                    duration=duration_str,
                )
            )
            cover_path = promoted.path

        # 图文内容
        graphics_contents: list[CardGraphicsContent] = []
        for graphics in result.graphics_contents:
            path = await graphics.get_path()
            graphics_contents.append(
                CardGraphicsContent(
                    path=path.as_uri(),
                    text_before=graphics.text_before,
                    text_after=graphics.text_after,
                    alt=graphics.alt,
                )
            )

        # 内容类型推断（允许解析器通过 extra 显式指定）
        content_type = result.extra.get("content_type")
        if content_type is None:
            if video_contents:
                content_type = "视频"
            elif graphics_contents:
                content_type = "图文"
            elif img_contents:
                content_type = "动态"
            elif result.repost:
                content_type = "动态"

        # 转发
        repost = await self._resolve_parse_result(result.repost) if result.repost else None

        # 播放按钮 & 字体（使用 CommonRenderer 定义的常量，保持一致）
        play_icon_uri = (
            CommonRenderer.DEFAULT_VIDEO_BUTTON_PATH.as_uri()
            if CommonRenderer.DEFAULT_VIDEO_BUTTON_PATH.exists()
            else None
        )
        font_path = pconfig.custom_font or CommonRenderer.DEFAULT_FONT_PATH
        font_uri = font_path.as_uri() if font_path.exists() else None

        return CardData(
            title=result.title,
            text=result.text,
            formartted_datetime=result.formartted_datetime,
            extra_info=result.extra_info,
            platform=platform,
            author=author,
            video_contents=video_contents,
            cover_path=cover_path,
            img_contents=img_contents,
            graphics_contents=graphics_contents,
            content_type=content_type,
            play_icon_uri=play_icon_uri,
            font_uri=font_uri,
            repost=repost,
        )
