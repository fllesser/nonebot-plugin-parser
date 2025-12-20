from typing import Any
from pathlib import Path
from typing_extensions import override

from nonebot import require

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import template_to_pic

from .base import ParseResult, ImageRenderer


class HtmlRenderer(ImageRenderer):
    """HTML 渲染器"""

    @override
    async def render_image(self, result: ParseResult) -> bytes:
        """使用 HTML 绘制通用社交媒体帖子卡片

        Args:
            result: 解析结果

        Returns:
            PNG 图片的字节数据
        """
        # 准备模板数据
        template_data = await self._resolve_parse_result(result)

        # 渲染图片
        return await template_to_pic(
            template_path=str(self.templates_dir),
            template_name="card.html.jinja",
            templates={"result": template_data},
            pages={
                "viewport": {"width": 800, "height": 100},  # 高度会自动调整
                "base_url": f"file://{self.templates_dir}",
            },
        )

    async def _resolve_parse_result(self, result: ParseResult) -> dict[str, Any]:
        """解析 ParseResult 为模板可用的字典数据，并处理异步资源路径"""
        data: dict[str, Any] = {
            "title": result.title,
            "text": result.text,
            "formartted_datetime": result.formartted_datetime,
            "extra_info": result.extra_info,
        }

        if result.platform:
            data["platform"] = {
                "display_name": result.platform.display_name,
                "name": result.platform.name,
            }
            # 尝试获取平台 logo
            logo_path = Path(__file__).parent / "resources" / f"{result.platform.name}.png"
            if logo_path.exists():
                data["platform"]["logo_path"] = logo_path.as_uri()

        # 处理作者信息
        if result.author:
            avatar_path = await result.author.get_avatar_path()
            data["author"] = {
                "name": result.author.name,
                "avatar_path": avatar_path.as_uri() if avatar_path else None,
            }

        # 处理封面
        cover_path = await result.cover_path
        if cover_path:
            data["cover_path"] = cover_path.as_uri()

        # 处理图片内容
        img_contents = []
        for img in result.img_contents:
            path = await img.get_path()
            img_contents.append({"path": path.as_uri()})
        data["img_contents"] = img_contents

        # 处理图文内容
        graphics_contents = []
        for graphics in result.graphics_contents:
            path = await graphics.get_path()
            graphics_contents.append(
                {
                    "path": path.as_uri(),
                    "text": graphics.text,
                    "alt": graphics.alt,
                }
            )
        data["graphics_contents"] = graphics_contents

        # 处理转发内容
        if result.repost:
            data["repost"] = await self._resolve_parse_result(result.repost)

        return data
