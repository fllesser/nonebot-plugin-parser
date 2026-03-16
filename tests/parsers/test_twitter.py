import asyncio

import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_video():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    urls = [
        "https://x.com/Fortnite/status/1904171341735178552",
    ]

    async def parse_video(url: str):
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析推特视频")
        result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{result}")

        assert result.video, "视频内容为空"
        path = await result.video.path_task.get()
        assert path.exists(), "视频不存在"
        cover_path = await result.video.cover.get()
        assert cover_path, "封面不存在"

    await asyncio.gather(*[parse_video(url) for url in urls])


@pytest.mark.asyncio
async def test_img():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    urls = [
        "https://x.com/Fortnite/status/1870484479980052921",  # 单图
        "https://x.com/chitose_yoshino/status/1841416254810378314",  # 多图
    ]

    async def parse_img(url: str):
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析推特图片")
        result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{result}")
        img_contents = result.img_contents
        assert img_contents, "图片内容为空"
        for img_content in img_contents:
            path = await img_content.path_task.get()
            assert path.exists(), "图片不存在"

    await asyncio.gather(*[parse_img(url) for url in urls])


@pytest.mark.asyncio
async def test_gif():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    urls = [
        "https://x.com/Dithmenos9/status/1966798448499286345",  # gif
    ]

    async def parse_gif(url: str):
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"

        logger.info(f"{url} | 开始解析推特 GIF")
        result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{result}")

        dynamic_contents = result.dynamic_contents
        assert dynamic_contents, "GIF 内容为空"
        for dynamic_content in dynamic_contents:
            path = await dynamic_content.path_task.get()
            assert path.exists(), "GIF 不存在"

    await asyncio.gather(*[parse_gif(url) for url in urls])


@pytest.mark.asyncio
async def test_repost():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    url = "https://x.com/matcha__ore_p/status/2025067664830497203?s=46"

    keyword, searched = parser.search_url(url)
    assert searched, "无法匹配 URL"

    logger.info(f"{url} | 开始解析推特转发")
    result = await parser.parse(keyword, searched)
    logger.debug(f"{url} | 解析结果: \n{result}")

    repost = result.repost
    assert repost, "转发为空"
