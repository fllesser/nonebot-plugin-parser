import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_x():
    from nonebot_plugin_resolver2.download import download_img, download_video
    from nonebot_plugin_resolver2.matchers.twitter import parse_x_url

    urls = [
        "https://x.com/Fortnite/status/1904171341735178552",  # 视频
        "https://x.com/Fortnite/status/1870484479980052921",  # 单图
        "https://x.com/chitose_yoshino/status/1841416254810378314",  # 多图
    ]
    for url in urls:
        logger.info(f"开始解析 {url}")
        video_url, pic_urls = await parse_x_url(url)
        if video_url:
            logger.info(f"视频: {video_url}")
            video_path = await download_video(video_url)
            assert video_path
            logger.success(f"视频下载成功 {url}")
        if pic_urls:
            logger.info(f"图片: {pic_urls}")
            tasks = [download_img(url=pic_url) for pic_url in pic_urls]
            img_paths = await asyncio.gather(*tasks)
            assert img_paths
            logger.success(f"图片下载成功 {url}")
