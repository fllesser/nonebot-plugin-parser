"""Instagram 链接解析落盘：卡片 + 媒体 + 元数据。用法: python scripts/instagram_delivery.py <url>"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter


def _slug_from_url(url: str) -> str:
    m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url, re.I)
    if m:
        return m.group(1)
    return re.sub(r"[^\w.-]+", "_", url)[:32]


async def _copy_path_task(path_task, dest: Path) -> bool:
    local = await path_task.safe_get()
    if not local or not local.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(local.read_bytes())
    return True


async def run_delivery(url: str, out_dir: Path) -> None:
    os.environ.setdefault("ENVIRONMENT", "dev")
    nonebot.init()
    nonebot.get_driver().register_adapter(OnebotV11Adapter)
    nonebot.load_from_toml("pyproject.toml")

    from nonebot_plugin_parser.parsers import InstagramParser
    from nonebot_plugin_parser.parsers.data import ImageContent, VideoContent
    from nonebot_plugin_parser.renders import get_renderer

    parser = InstagramParser()
    keyword, searched = parser.search_url(url)
    if not searched:
        raise SystemExit(f"无法匹配 Instagram 链接: {url}")

    result = await parser.parse(keyword, searched)
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "input_url": url,
        "matched_keyword": keyword,
        "normalized_url": result.url,
        "title": result.title,
        "author": result.author.name if result.author else None,
        "timestamp": result.timestamp,
        "text_preview": (result.text or "")[:500],
        "content_count": len(result.contents),
        "extra": dict(result.extra),
        "has_video": result.video is not None,
        "image_count": len(result.img_contents),
        "video_duration": result.video.duration if result.video else None,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if result.author and result.author.avatar:
        await _copy_path_task(result.author.avatar, out_dir / "author_avatar.jpg")

    await result.ensure_downloads_complete(img_only=True)
    try:
        await result.ensure_downloads_complete(img_only=False)
    except Exception:
        pass

    idx = 0
    video_saved = False
    for content in result.contents:
        if isinstance(content, ImageContent):
            path = await content.path_task.safe_get()
            ext = path.suffix if path else ".jpg"
            if await _copy_path_task(
                content.path_task, out_dir / f"media_{idx:02d}_image{ext}"
            ):
                idx += 1
        elif isinstance(content, VideoContent):
            path = await content.path_task.safe_get()
            ext = path.suffix if path else ".mp4"
            if await _copy_path_task(
                content.path_task, out_dir / f"media_{idx:02d}_video{ext}"
            ):
                video_saved = True
            if content.cover:
                cover_path = await content.cover.safe_get()
                cover_ext = cover_path.suffix if cover_path else ".jpg"
                await _copy_path_task(
                    content.cover, out_dir / f"media_{idx:02d}_cover{cover_ext}"
                )
            idx += 1

    download_url = result.url or url
    video_path = out_dir / "media_00_video.mp4"
    if result.video and not video_saved and not video_path.is_file():
        ytdlp = Path(sys.executable).parent / "yt-dlp.exe"
        if not ytdlp.is_file():
            ytdlp = Path("yt-dlp")
        subprocess.run(
            [
                str(ytdlp),
                "-o",
                str(out_dir / "media_00_video.%(ext)s"),
                "-f",
                "best",
                "--merge-output-format",
                "mp4",
                download_url,
            ],
            check=False,
        )

    Renderer = get_renderer(result.platform.name)
    renderer = Renderer(result)
    card_bytes = await renderer.render_image()
    (out_dir / "card.png").write_bytes(card_bytes)
    (out_dir / "cover_card.png").write_bytes(card_bytes)

    readme = "\n".join(
        [
            f"URL: {url}",
            f"规范化: {result.url}",
            f"标题: {result.title}",
            f"作者: {result.author.name if result.author else None}",
            "",
            "card.png / cover_card.png — 摘要卡片",
            "author_avatar.jpg — 作者头像",
            "media_XX_* — 解析得到的媒体",
            "meta.json — 元数据",
        ]
    )
    (out_dir / "README.txt").write_text(readme, encoding="utf-8")

    print("saved_dir:", out_dir.resolve())
    print("card_bytes:", len(card_bytes))
    print("media_items:", idx)
    print("title:", result.title)
    print("author:", result.author.name if result.author else None)
    if video_path.is_file():
        print("video:", video_path.name, video_path.stat().st_size)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default=None, help="输出目录，默认 instagram_<shortcode>_out")
    args = ap.parse_args()
    slug = _slug_from_url(args.url)
    out_dir = Path(args.out) if args.out else Path(f"instagram_{slug}_out")
    asyncio.run(run_delivery(args.url, out_dir))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    main()
