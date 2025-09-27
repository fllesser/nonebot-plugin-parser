import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.parsers.data import ImageContent, VideoContent
    from nonebot_plugin_resolver2.parsers.twitter import TwitterParser

    urls = [
        "https://x.com/Fortnite/status/1904171341735178552",  # 视频
        "https://x.com/Fortnite/status/1870484479980052921",  # 单图
        "https://x.com/chitose_yoshino/status/1841416254810378314",  # 多图
    ]

    async def parse_x(url: str):
        logger.info(f"开始解析推特 {url}")
        content = await TwitterParser.parse_x_url_new(url)
        if content is None:
            raise ValueError("解析结果为空")
        elif isinstance(content, VideoContent):
            logger.info(f"{url} | 解析为视频: {content.video_url}")
            video_path = await DOWNLOADER.download_video(content.video_url)
            assert video_path.exists()
            logger.success(f"{url} | 视频解析并下载成功")
        elif isinstance(content, ImageContent):
            logger.info(f"{url} | 解析为图片: {content.pic_urls}")
            img_paths = await DOWNLOADER.download_imgs_without_raise(content.pic_urls)
            assert len(img_paths) == len(content.pic_urls)
            for img_path in img_paths:
                assert img_path.exists()
            logger.success(f"{url} | 图片解析并下载成功")

    await asyncio.gather(*(parse_x(url) for url in urls))
