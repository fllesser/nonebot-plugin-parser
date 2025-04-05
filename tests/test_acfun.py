import pytest


@pytest.mark.asyncio
async def test_parse_acfun_url():
    import asyncio

    from nonebot_plugin_resolver2.parsers.acfun import (
        download_m3u8_videos,
        merge_ac_file_to_mp4,
        parse_acfun_url,
        parse_m3u8,
    )

    urls = ["https://www.acfun.cn/v/ac46593564", "https://www.acfun.cn/v/ac40867941"]
    for url in urls:
        acid = url.split("/")[-1].split("ac")[1]
        m3u8s_url, video_name = await parse_acfun_url(url)
        assert m3u8s_url
        assert video_name
        m3u8_full_urls, ts_names, output_file_name = await parse_m3u8(m3u8s_url)
        assert m3u8_full_urls
        assert ts_names
        assert output_file_name
        await asyncio.gather(*[download_m3u8_videos(url, f"acfun{acid}_{i}") for i, url in enumerate(m3u8_full_urls)])
        await merge_ac_file_to_mp4(ts_names, output_file_name)
