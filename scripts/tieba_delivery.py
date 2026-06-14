"""贴吧链接落盘测试。用法: python scripts/tieba_delivery.py <url>"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter


def _slug(url: str) -> str:
    import re

    m = re.search(r"/p/(\d+)", url)
    return f"tieba_{m.group(1)}_out" if m else "tieba_out"


async def run(url: str, out_dir: Path) -> None:
    os.environ.setdefault("ENVIRONMENT", "dev")
    nonebot.init()
    nonebot.get_driver().register_adapter(OnebotV11Adapter)
    nonebot.load_from_toml("pyproject.toml")

    from nonebot_plugin_parser.parsers import TiebaParser
    from nonebot_plugin_parser.parsers.data import ImageContent, VideoContent
    from nonebot_plugin_parser.renders import get_renderer

    parser = TiebaParser()
    keyword, searched = parser.search_url(url)
    if not searched:
        raise SystemExit(f"无法匹配: {url}")

    result = await parser.parse(keyword, searched)
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "url": url,
        "title": result.title,
        "text": result.text,
        "author": result.author.name if result.author else None,
        "extra": dict(result.extra),
        "content_count": len(result.contents),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if result.author and result.author.avatar:
        ap = await result.author.avatar.safe_get()
        if ap and ap.exists():
            (out_dir / "author_avatar.jpg").write_bytes(ap.read_bytes())

    await result.ensure_downloads_complete(img_only=True)
    try:
        await result.ensure_downloads_complete(img_only=False)
    except Exception:
        pass

    idx = 0
    for c in result.contents:
        if isinstance(c, ImageContent):
            p = await c.path_task.safe_get()
            ext = p.suffix if p else ".jpg"
            if p and p.exists():
                (out_dir / f"media_{idx:02d}_image{ext}").write_bytes(p.read_bytes())
            idx += 1
        elif isinstance(c, VideoContent):
            p = await c.path_task.safe_get()
            ext = p.suffix if p else ".mp4"
            if p and p.exists():
                (out_dir / f"media_{idx:02d}_video{ext}").write_bytes(p.read_bytes())
            if c.cover:
                cp = await c.cover.safe_get()
                if cp and cp.exists():
                    (out_dir / f"media_{idx:02d}_cover{cp.suffix or '.jpg'}").write_bytes(
                        cp.read_bytes()
                    )
            idx += 1

    Renderer = get_renderer(result.platform.name)
    card = await Renderer(result).render_image()
    (out_dir / "card.png").write_bytes(card)
    (out_dir / "cover_card.png").write_bytes(card)

    print("saved:", out_dir.resolve())
    print("title:", result.title)
    print("text:", result.text)
    print("author:", result.author.name if result.author else None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    out = Path(args.out or _slug(args.url))
    asyncio.run(run(args.url, out))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    main()
