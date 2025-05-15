import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_kuaishou_video():
    """
    测试快手视频解析
    - https://www.kuaishou.com/short-video/3xhjgcmir24m4nm
    - https://v.kuaishou.com/1ff8QP
    - https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc
    """
    from nonebot_plugin_resolver2.download import download_video, fmt_size
    from nonebot_plugin_resolver2.parsers import KuaishouParser

    kuaishou_parser = KuaishouParser()

    test_urls = [
        "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",
        "https://v.kuaishou.com/2yAnzeZ",
        "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc",
    ]

    async def test_parse_url(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")
        video_info = await kuaishou_parser.parse_url(url)

        logger.debug(f"{url} | title: {video_info.title}")
        assert video_info.title, "视频标题为空"

        logger.debug(f"{url} | cover_url: {video_info.cover_url}")
        # assert video_info.cover_url, "视频封面URL为空"

        logger.debug(f"{url} | video_url: {video_info.video_url}")
        assert video_info.video_url, "视频URL为空"

        # 下载视频
        video_path = await download_video(video_info.video_url)
        logger.debug(f"{url} | 视频下载完成: {video_path}, 视频{fmt_size(video_path)}")

        if video_info.author:
            logger.debug(f"{url} | author: {video_info.author}")

        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[test_parse_url(url) for url in test_urls])
