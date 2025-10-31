import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_graphics():
    """测试微博图片解析"""
    from nonebot_plugin_parser.parsers import WeiBoParser

    parser = WeiBoParser()

    urls = [
        "https://weibo.com/7207262816/P5kWdcfDe",
        "https://m.weibo.cn/status/5155768539808352",
    ]

    async def parse_graphics(url: str) -> None:
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        if img_contents := parse_result.img_contents:
            for img_content in img_contents:
                path = await img_content.get_path()
                assert path.exists()
        logger.success(f"{url} | 微博图文解析成功")

    await asyncio.gather(*[parse_graphics(url) for url in urls])


async def test_repost():
    from nonebot_plugin_parser.parsers import WeiBoParser

    parser = WeiBoParser()

    urls = [
        "https://mapp.api.weibo.cn/fx/77eaa5c2f741894631a87fc4806a1f05.html",
        "https://weibo.com/1694917363/Q0KtXh6z2",
    ]

    async def parse_repost(url) -> None:
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析微博转发")
        parse_result = await parser.parse(keyword, searched)
        repost = parse_result.repost
        assert repost
        logger.debug(f"{url} | 转发内容: \n{repost}")

        if img_contents := repost.img_contents:
            for img_content in img_contents:
                path = await img_content.get_path()
                assert path.exists()

        if video_contents := repost.video_contents:
            for video_content in video_contents:
                path = await video_content.get_path()
                assert path.exists()

    await asyncio.gather(*[parse_repost(url) for url in urls])


@pytest.mark.asyncio
async def test_video():
    """测试微博视频解析"""
    from nonebot_plugin_parser.parsers import WeiBoParser

    parser = WeiBoParser()

    urls = [
        "https://weibo.com/tv/show/1034:5007449447661594?mid=5007452630158934",
        "https://video.weibo.com/show?fid=1034:5145615399845897",
        "https://weibo.com/7207262816/O70aCbjnd",
        "http://m.weibo.cn/status/5112672433738061",
    ]

    async def parse_video(url: str) -> None:
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: {parse_result}")
        video_paths = parse_result.video_contents
        for video_path in video_paths:
            video_path = await video_path.get_path()
            assert video_path.exists()
        logger.success(f"{url} | 微博视频下载成功")

    await asyncio.gather(*[parse_video(url) for url in urls])


@pytest.mark.asyncio
async def test_text():
    """测试微博纯文本"""
    from nonebot_plugin_parser.parsers import WeiBoParser

    parser = WeiBoParser()

    urls = [
        "https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html",
        "https://weibo.com/3144744040/PvoG6c1AR",
        "https://weibo.com/3144744040/PiTAYaTKQ",
        "https://weibo.com/1157864602/Q0PtH9Yux",
    ]

    async def parse_text(url: str) -> None:
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.text
        logger.success(f"{url} | 微博纯文本解析成功")

    await asyncio.gather(*[parse_text(url) for url in urls])
