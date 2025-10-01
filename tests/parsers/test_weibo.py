import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_graphics():
    """测试微博图片解析"""
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    urls = [
        "https://weibo.com/7207262816/P5kWdcfDe",
        "https://m.weibo.cn/status/5155768539808352",
        "https://mapp.api.weibo.cn/fx/77eaa5c2f741894631a87fc4806a1f05.html",
    ]

    async def parse_graphics(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        parse_result = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.pic_paths
        assert len(parse_result.pic_paths) > 0
        logger.success(f"{url} | 微博图文解析成功")

    await asyncio.gather(*[parse_graphics(url) for url in urls])


@pytest.mark.asyncio
async def test_video():
    """测试微博视频解析"""
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    urls = [
        "https://weibo.com/tv/show/1034:5007449447661594?mid=5007452630158934",
        "https://video.weibo.com/show?fid=1034:5145615399845897",
        "https://weibo.com/7207262816/O70aCbjnd",
        "http://m.weibo.cn/status/5112672433738061",
        "https://weibo.com/1694917363/Q0KtXh6z2",
    ]

    async def parse_video(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        parse_result = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: {parse_result}")
        assert parse_result.video_path
        assert parse_result.video_path.exists()
        logger.success(f"{url} | 微博视频下载成功")

    await asyncio.gather(*[parse_video(url) for url in urls])


@pytest.mark.asyncio
async def test_text():
    """测试微博纯文本"""
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    urls = [
        "https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html",
        "https://weibo.com/3144744040/PvoG6c1AR",
        "https://weibo.com/3144744040/PiTAYaTKQ",
        "https://weibo.com/1157864602/Q0PtH9Yux",
    ]

    async def parse_text(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        parse_result = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title
        logger.success(f"{url} | 微博纯文本解析成功")

    await asyncio.gather(*[parse_text(url) for url in urls])
