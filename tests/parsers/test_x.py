import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    from nonebot_plugin_resolver2.parsers.data import ImageContent, VideoContent
    from nonebot_plugin_resolver2.parsers.twitter import TwitterParser

    urls = [
        "https://x.com/Fortnite/status/1904171341735178552",  # 视频
        "https://x.com/Fortnite/status/1870484479980052921",  # 单图
        "https://x.com/chitose_yoshino/status/1841416254810378314",  # 多图
        "https://x.com/Dithmenos9/status/1966798448499286345",  # gif
    ]

    async def parse_x(url: str):
        logger.info(f"开始解析推特 {url}")
        content = await TwitterParser.parse_x_url(url)
        if content is None:
            raise ValueError("解析结果为空")
        elif isinstance(content, VideoContent):
            logger.info(f"{url} | 解析为视频: {content.video_path}")
            assert content.video_path
            assert content.video_path.exists()
            logger.success(f"{url} | 视频解析并下载成功")
        elif isinstance(content, ImageContent):
            logger.info(f"{url} | 解析为图片: {content.pic_paths}")
            assert content.pic_paths
            assert len(content.pic_paths) > 0
            for img_path in content.pic_paths:
                assert img_path.exists()
            logger.success(f"{url} | 图片解析并下载成功")

    await asyncio.gather(*(parse_x(url) for url in urls))
