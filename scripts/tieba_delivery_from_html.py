"""用 Relay 保存的 HTML 测贴吧解析（无需 Cookie 进 curl）。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

HTML_PATH = Path("scripts/_tieba_saved_page.html")
URL = "https://tieba.baidu.com/p/10780369243/"


async def main() -> None:
    if not HTML_PATH.is_file():
        raise SystemExit(f"缺少 {HTML_PATH}，先用 relay 导出 HTML")

    html_text = HTML_PATH.read_text(encoding="utf-8", errors="replace")
    os.environ.setdefault("ENVIRONMENT", "dev")
    nonebot.init()
    nonebot.get_driver().register_adapter(OnebotV11Adapter)
    nonebot.load_from_toml("pyproject.toml")

    from nonebot_plugin_parser.parsers.tieba import TiebaParser
    from nonebot_plugin_parser.renders import get_renderer

    parser = TiebaParser()
    result = await parser._result_from_html(html_text, URL, "10780369243")

    out = Path("tieba_10780369243_out")
    out.mkdir(exist_ok=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "title": result.title,
                "text": result.text,
                "author": result.author.name if result.author else None,
                "extra": result.extra,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    await result.ensure_downloads_complete(img_only=False)
    Renderer = get_renderer(result.platform.name)
    card = await Renderer(result).render_image()
    (out / "card.png").write_bytes(card)
    print("title:", result.title)
    print("text:", result.text)
    print("saved:", out.resolve())


if __name__ == "__main__":
    asyncio.run(main())
