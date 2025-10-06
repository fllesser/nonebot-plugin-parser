import asyncio
import re

from nonebot import logger


async def test_video():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    urls = [
        "https://x.com/Fortnite/status/1904171341735178552",
    ]

    async def parse_video(url: str):
        matched = next(re.search(pattern, url) for _, pattern in parser.patterns)
        assert matched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析推特视频")
        result = await parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{result}")
        assert result.title, "标题为空"
        video_contents = result.video_contents
        assert video_contents, "视频内容为空"
        for video_content in video_contents:
            path = await video_content.get_path()
            assert path.exists(), "视频不存在"
            cover_path = await video_content.get_cover_path()
            assert cover_path, "封面不存在"

    await asyncio.gather(*[parse_video(url) for url in urls])


async def test_img():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    urls = [
        "https://x.com/Fortnite/status/1870484479980052921",  # 单图
        "https://x.com/chitose_yoshino/status/1841416254810378314",  # 多图
    ]

    async def parse_img(url: str):
        matched = next(re.search(pattern, url) for _, pattern in parser.patterns)
        assert matched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析推特图片")
        result = await parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{result}")
        img_contents = result.img_contents
        assert img_contents, "图片内容为空"
        for img_content in img_contents:
            path = await img_content.get_path()
            assert path.exists(), "图片不存在"

    await asyncio.gather(*[parse_img(url) for url in urls])


async def test_gif():
    from nonebot_plugin_parser.parsers import TwitterParser

    parser = TwitterParser()

    urls = [
        "https://x.com/Dithmenos9/status/1966798448499286345",
    ]

    async def parse_gif(url: str):
        matched = next(re.search(pattern, url) for _, pattern in parser.patterns)
        assert matched, "无法匹配 URL"
        logger.info(f"{url} | 开始解析推特 GIF")
        result = await parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{result}")
        gif_contents = result.dynamic_contents
        assert gif_contents, "GIF 内容为空"
        for gif_content in gif_contents:
            path = await gif_content.get_path()
            assert path.exists(), "GIF 不存在"

    await asyncio.gather(*[parse_gif(url) for url in urls])
