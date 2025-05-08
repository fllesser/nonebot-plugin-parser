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

    async def parse_x_url_test(url: str):
        logger.info(f"开始解析推特 {url}")
        video_url, pic_urls = await parse_x_url(url)
        if video_url:
            logger.info(f"{url} | 解析为视频: {video_url}")
            video_path = await download_video(video_url)
            assert video_path.exists()
            logger.success(f"{url} | 视频解析并下载成功")
        if pic_urls:
            logger.info(f"{url} | 解析为图片: {pic_urls}")
            tasks = [download_img(url=pic_url) for pic_url in pic_urls]
            img_paths = await asyncio.gather(*tasks)
            assert len(img_paths) == len(pic_urls)
            for img_path in img_paths:
                assert img_path.exists()
            logger.success(f"{url} | 图片解析并下载成功")

    await asyncio.gather(*[parse_x_url_test(url) for url in urls])
