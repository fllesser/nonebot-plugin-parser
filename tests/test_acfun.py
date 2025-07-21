import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse_acfun_url():
    from nonebot_plugin_resolver2.download.utils import fmt_size
    from nonebot_plugin_resolver2.parsers import AcfunParser

    urls = ["https://www.acfun.cn/v/ac46593564", "https://www.acfun.cn/v/ac40867941"]
    acfun_parser = AcfunParser()

    async def parse_acfun_url(url: str) -> None:
        acid = int(url.split("/")[-1].split("ac")[1])
        logger.info(f"{url} | 开始解析视频 acid: {acid}")
        m3u8s_url, video_desc = await acfun_parser.parse_url(url)
        assert m3u8s_url
        assert video_desc
        logger.debug(f"{url} | m3u8s_url: {m3u8s_url}, video_desc: {video_desc}")

        logger.info(f"{url} | 开始下载视频")
        video_file = await acfun_parser.download_video(m3u8s_url, acid)
        assert video_file
        logger.info(f"{url} | 视频下载成功, 视频{fmt_size(video_file)}")

    await asyncio.gather(*[parse_acfun_url(url) for url in urls])
