import asyncio

import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_parse():
    """小红书解析测试"""
    # 需要 ck 才能解析， 暂时不测试
    from nonebot_plugin_parser.parsers import XiaoHongShuParser

    parser = XiaoHongShuParser()
    urls = [
        "https://www.xiaohongshu.com/explore/68f963260000000004005843?xsec_token=ABn8T0lrJdPfRlWpNvLoYWTd0x54P44tsJtYgqhujHTjo=&xsec_source=pc_feed"
    ]

    async def parse(url: str) -> None:
        logger.info(f"{url} | 开始解析小红书")
        # 使用 patterns 匹配 URL
        keyword, searched = parser.search_url(url)
        assert searched, f"无法匹配 URL: {url}"
        try:
            result = await parser.parse(keyword, searched)
        except Exception as e:
            pytest.skip(f"{url} | 链接失效，跳过测试: {e}")

        logger.debug(f"{url} | 解析结果: \n{result}")
        for content in result.contents:
            path = await content.get_path()
            assert path.exists()

    await asyncio.gather(*[parse(url) for url in urls])
