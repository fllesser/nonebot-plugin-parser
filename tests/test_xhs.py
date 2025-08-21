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
        "https://www.xiaohongshu.com/discovery/item/685fd0e00000000024008b56?app_platform=android&ignoreEngage=true&app_version=8.87.6&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBc7kDk5WA32hs6hpCZ4jOhP1n0l8OeJ0kOeeUOoEHPl8%3D&author_share=1&xhsshare=QQ&shareRedId=N0w7NTk7ND82NzUyOTgwNjY0OTc4Sz9N&apptime=1751343431&share_id=c644022d3b18407d95807a10b14f0658&share_channel=qq&qq_aio_chat_type=2",
    ]

    async def test_parse_url(url: str) -> None:
        logger.info(f"{url} | 开始解析小红书")
        parse_result = await xhs_parser.parse_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title
        logger.success(f"{url} | 小红书解析成功")

    await asyncio.gather(*[test_parse_url(url) for url in urls])
