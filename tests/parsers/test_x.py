import asyncio

from nonebot import logger


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
        contents = await TwitterParser.parse_x_url(url)
        for content in contents:
            if isinstance(content, VideoContent):
                assert content.path.exists()
            elif isinstance(content, ImageContent):
                assert content.path.exists()
            else:
                pass

    await asyncio.gather(*(parse_x(url) for url in urls))
