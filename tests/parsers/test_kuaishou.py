import asyncio

import httpx
from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    """测试快手视频解析"""
    from nonebot_plugin_resolver2.download.utils import fmt_size
    from nonebot_plugin_resolver2.parsers import KuaishouParser

    parser = KuaishouParser()

    test_urls = [
        "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",
        "https://v.kuaishou.com/2yAnzeZ",  # 视频
        "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc",  # 视频
        "https://v.kuaishou.com/nmcrgMMR",  # 图集
    ]

    async def parse(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")
        try:
            parse_result = await parser.parse_url(url)
        except httpx.ConnectTimeout:
            pytest.skip(f"解析超时(action 网络问题) ({url})")

        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title, "视频标题为空"

        if video_path := parse_result.video_path:
            assert video_path.exists()
            logger.debug(f"{url} | 视频下载完成: {video_path}, 视频{fmt_size(video_path)}")

        # 检查图片
        if pic_paths := parse_result.pic_paths:
            logger.debug(f"{url} | 图片下载完成: {pic_paths}")
            assert len(pic_paths) > 0, "图片下载数量为0"

        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[parse(url) for url in test_urls])
