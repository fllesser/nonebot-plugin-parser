import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_xiaohongshu():
    """小红书解析测试"""
    # 需要 ck 才能解析， 暂时不测试
    from nonebot_plugin_resolver2.parsers import XiaoHongShuParser

    xhs_parser = XiaoHongShuParser()
    urls = [
        "http://xhslink.com/m/3RbKPhJlIB3",  # 图文短链
        "http://xhslink.com/m/1nhWDzSpHXB",  # 视频短链
        "https://www.xiaohongshu.com/explore/68949dfb000000002303595f?xsec_token=AB6pSzFZLKoM2TeirLL1hPUjNbBnkpj_B4HhBfpWr47vg=&xsec_source=",
    ]

    async def test_parse_url(url: str) -> None:
        logger.info(f"{url} | 开始解析小红书")
        parse_result = await xhs_parser.parse_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title
        logger.success(f"{url} | 小红书解析成功")

    await asyncio.gather(*[test_parse_url(url) for url in urls])
