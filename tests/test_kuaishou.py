import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse_by_api():
    """测试快手视频解析 based on api"""
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.download.utils import fmt_size
    from nonebot_plugin_resolver2.parsers import KuaishouParser

    parser = KuaishouParser()

    test_urls = [
        "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",
        "https://v.kuaishou.com/2yAnzeZ",
        "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc",
    ]

    async def test_parse_url(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")
        video_info = await parser.parse_url_by_api(url)

        logger.debug(f"{url} | title: {video_info.title}")
        assert video_info.title, "视频标题为空"

        logger.debug(f"{url} | cover_url: {video_info.cover_url}")
        # assert video_info.cover_url, "视频封面URL为空"

        logger.debug(f"{url} | video_url: {video_info.video_url}")
        assert video_info.video_url, "视频URL为空"

        # 下载视频
        video_path = await DOWNLOADER.download_video(video_info.video_url)
        logger.debug(f"{url} | 视频下载完成: {video_path}, 视频{fmt_size(video_path)}")

        if video_info.author:
            logger.debug(f"{url} | author: {video_info.author}")

        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[test_parse_url(url) for url in test_urls])


@pytest.mark.asyncio
async def test_parse():
    """测试快手视频解析"""
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.download.utils import fmt_size
    from nonebot_plugin_resolver2.parsers import KuaishouParser

    parser = KuaishouParser()

    test_urls = [
        # "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",  # 视频 action 测试易失败
        "https://v.kuaishou.com/2yAnzeZ",  # 视频
        "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc",  # 视频
        # "https://v.kuaishou.com/2xZPkuV",  # 图集
    ]

    async def test_parse_url(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")
        video_info = await parser.parse_url(url)

        logger.debug(f"{url} | title: {video_info.title}")
        assert video_info.title, "视频标题为空"

        logger.debug(f"{url} | cover_url: {video_info.cover_url}")
        assert video_info.cover_url, "视频封面URL为空"

        if video_info.video_url:
            logger.debug(f"{url} | video_url: {video_info.video_url}")
            # 下载视频
            video_path = await DOWNLOADER.download_video(video_info.video_url, ext_headers=parser.v_headers)
            logger.debug(f"{url} | 视频下载完成: {video_path}, 视频{fmt_size(video_path)}")

        if video_info.pic_urls:
            logger.debug(f"{url} | pic_urls: {video_info.pic_urls}")
            # 下载图片
            img_paths = await DOWNLOADER.download_imgs_without_raise(video_info.pic_urls, ext_headers=parser.v_headers)
            logger.debug(f"{url} | 图片下载完成: {img_paths}")
            assert len(img_paths) == len(video_info.pic_urls), "图片下载数量不一致"

        if video_info.author:
            logger.debug(f"{url} | author: {video_info.author}")

        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[test_parse_url(url) for url in test_urls])
