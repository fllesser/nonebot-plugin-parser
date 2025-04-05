from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse_acfun_url():
    from nonebot_plugin_resolver2.parsers.acfun import parse_acfun_url

    urls = ["https://www.acfun.cn/v/ac46593564", "https://www.acfun.cn/v/ac40867941"]
    for url in urls:
        url_m3u8s, video_name = await parse_acfun_url(url)
        logger.info(url_m3u8s)
        logger.info(video_name)
