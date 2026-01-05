import datetime

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
        """使用 HTML 绘制通用社交媒体帖子卡片"""
        # 准备模板数据
        template_data = await self._resolve_parse_result(result)

        # 处理模板针对
        template_name = "card.html.jinja"
        if result.platform:
            # 添加存在性验证
            file_name = f"{str(result.platform.name).lower()}.html.jinja"
            if (self.templates_dir / file_name).exists():
                template_name = file_name

        # 渲染图片
        return await template_to_pic(
            template_path=str(self.templates_dir),
            template_name=template_name,
            templates={"result": template_data,"rendering_time":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            pages={
                "viewport": {"width": 800, "height": 100},
                "base_url": f"file://{self.templates_dir}",
            },
        )

    async def _resolve_parse_result(self, result: ParseResult) -> dict[str, Any]:
        """解析 ParseResult 为模板可用的字典数据"""

        data: dict[str, Any] = {
            "title": result.title,
            "text": result.text,
            "formartted_datetime": result.formartted_datetime,
            "extra_info": result.extra_info,
            "extra": result.extra,
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

        if result.author:
            avatar_path = await result.author.get_avatar_path()
            author_id = getattr(result.author, "id", None)
            if not author_id and result.extra:
                author_id = result.extra.get("author_id")

            data["author"] = {
                "name": result.author.name,
                "id": author_id,  # 传递 UID
                "avatar_path": avatar_path.as_uri() if avatar_path else None,
            }

        cover_path = await result.cover_path
        if cover_path:
            data["cover_path"] = cover_path.as_uri()

        img_contents = []
        for img in result.img_contents:
            path = await img.get_path()
            img_contents.append({"path": path.as_uri()})
        data["img_contents"] = img_contents

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

        if result.repost:
            data["repost"] = await self._resolve_parse_result(result.repost)

        return data
