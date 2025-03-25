from nonebot.log import logger
import pytest


@pytest.mark.asyncio
async def test_x():
    from nonebot_plugin_resolver2.matchers.twitter import parse_x_url
    from nonebot_plugin_resolver2.parsers.base import ParseException

    urls = [
        "https://x.com/Fortnite/status/1904171341735178552",  # video
        "https://x.com/Fortnite/status/1870484479980052921",  # image
        "https://x.com/Fortnite/status/1904222508657561750",  # image
    ]
    for url in urls:
        try:
            video_url, pic_url = await parse_x_url(url)
            logger.info(f"资源 url: {video_url or pic_url}")
        except ParseException as e:
            logger.error(f"解析失败: {e}")
