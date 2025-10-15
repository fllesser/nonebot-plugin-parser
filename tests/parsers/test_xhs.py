import asyncio
import re

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    """小红书解析测试"""
    # 需要 ck 才能解析， 暂时不测试
    from nonebot_plugin_parser.parsers import XiaoHongShuParser

    xhs_parser = XiaoHongShuParser()
    urls = [
        "http://xhslink.com/o/9e33TIg4gc4",  # 图文短链
        "http://xhslink.com/o/9IteTIwy6WE",  # 视频短链
        # "https://www.xiaohongshu.com/explore/68949dfb000000002303595f?xsec_token=AB6pSzFZLKoM2TeirLL1hPUjNbBnkpj_B4HhBfpWr47vg=&xsec_source=",
        "https://www.xiaohongshu.com/discovery/item/68b6bc8a000000001c0311c4?app_platform=android&ignoreEngage=true&app_version=8.96.0&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBLD_3-DfBKy1ucXzJzbe4qMP4sNfBTFWJBrWaP_7iWpw%3D&author_share=1&xhsshare=QQ&shareRedId=ODs3RUk5ND42NzUyOTgwNjY3OTo8S0tK&apptime=1756856490&share_id=bdb1925c5c07432598852e7e44150820&share_channel=qq",
    ]

    async def parse(url: str) -> None:
        logger.info(f"{url} | 开始解析小红书")
        # 使用 patterns 匹配 URL
        matched = None
        for _, pattern in xhs_parser.patterns:
            matched = re.search(pattern, url)
            if matched:
                break
        assert matched, f"无法匹配 URL: {url}"
        parse_result = await xhs_parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        for content in parse_result.contents:
            path = await content.get_path()
            assert path.exists()

    await asyncio.gather(*[parse(url) for url in urls])
