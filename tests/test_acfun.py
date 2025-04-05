from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse_acfun_url():
    import asyncio

    from nonebot_plugin_resolver2.download import download_file_by_stream
    from nonebot_plugin_resolver2.parsers.acfun import (
        merge_ac_file_to_mp4,
        parse_acfun_url,
        parse_m3u8,
    )

    urls = ["https://www.acfun.cn/v/ac46593564", "https://www.acfun.cn/v/ac40867941"]
    for url in urls:
        acid = int(url.split("/")[-1].split("ac")[1])
        m3u8s_url, video_name = await parse_acfun_url(url)
        assert m3u8s_url
        assert video_name
        logger.debug(f"m3u8s_url: {m3u8s_url}, video_name: {video_name}")

        m3u8_full_urls = await parse_m3u8(m3u8s_url)
        assert m3u8_full_urls
        logger.debug(f"m3u8_full_urls: {m3u8_full_urls}")

        ts_paths = await asyncio.gather(*[download_file_by_stream(url) for url in m3u8_full_urls])
        video_file = await merge_ac_file_to_mp4(acid, ts_paths)
        assert video_file
