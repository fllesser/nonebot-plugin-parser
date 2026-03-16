import asyncio

import httpx
import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_parse():
    """测试快手视频解析"""
    from nonebot_plugin_parser.parsers import KuaiShouParser

    parser = KuaiShouParser()

    test_urls = [
        "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",
        "https://v.kuaishou.com/2yAnzeZ",  # 视频
        "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc",  # 视频
        "https://v.kuaishou.com/nmcrgMMR",  # 图集
    ]

    async def parse(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")
        keyword, searched = parser.search_url(url)
        assert searched, f"无法匹配 URL: {url}"

        try:
            result = await parser.parse(keyword, searched)
        except httpx.ConnectTimeout:
            pytest.skip(f"解析超时(action 网络问题) ({url})")

        logger.debug(f"{url} | 解析结果: \n{result}")
        assert result.title, "视频标题为空"

        await result.ensure_downloads_complete()

        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[parse(url) for url in test_urls])
