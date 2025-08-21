import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_weibo_pics():
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    urls = [
        "https://weibo.com/7207262816/P5kWdcfDe",
        "https://m.weibo.cn/status/5155768539808352",
    ]

    async def test_parse_share_url(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        video_info = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: {video_info}")
        assert video_info.pic_urls
        logger.success(f"{url} | 微博解析成功")

        files = await DOWNLOADER.download_imgs_without_raise(video_info.pic_urls, ext_headers=weibo_parser.ext_headers)
        assert len(files) == len(video_info.pic_urls)
        logger.success(f"{url} | 微博图文解析成功")

    await asyncio.gather(*[test_parse_share_url(url) for url in urls])


@pytest.mark.asyncio
async def test_weibo_video():
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    urls = [
        "https://video.weibo.com/show?fid=1034:5145615399845897",
        "https://weibo.com/7207262816/O70aCbjnd",
        "http://m.weibo.cn/status/5112672433738061",
        "https://weibo.com/1694917363/Q0KtXh6z2",
    ]

    async def test_parse_weibo_video(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        parse_result = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: {parse_result}")
        assert parse_result.video_url
        video_path = await DOWNLOADER.download_video(parse_result.video_url, ext_headers=weibo_parser.ext_headers)
        assert video_path
        logger.success(f"{url} | 微博视频下载成功")

    await asyncio.gather(*[test_parse_weibo_video(url) for url in urls])


@pytest.mark.asyncio
async def test_weibo_article():
    """测试微博纯文本"""
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    urls = [
        "https://weibo.com/3144744040/PvoG6c1AR",
        "https://weibo.com/3144744040/PiTAYaTKQ",
        "https://weibo.com/1157864602/Q0PtH9Yux",
    ]

    async def test_parse_weibo_article(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        parse_result = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: {parse_result}")

    await asyncio.gather(*[test_parse_weibo_article(url) for url in urls])
