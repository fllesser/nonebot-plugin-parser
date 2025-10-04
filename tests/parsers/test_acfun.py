import re

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    from nonebot_plugin_parser.parsers import AcfunParser
    from nonebot_plugin_parser.utils import fmt_size

    url = "https://www.acfun.cn/v/ac46593564"
    acfun_parser = AcfunParser()

    async def parse_acfun_url(url: str) -> None:
        logger.info(f"{url} | 开始解析 Acfun 视频")
        # 使用 patterns 匹配 URL
        matched = None
        for keyword, pattern in acfun_parser.patterns:
            matched = re.search(pattern, url)
            if matched:
                break
        assert matched, f"无法匹配 URL: {url}"
        parse_result = await acfun_parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")

        assert parse_result.title, "视频标题为空"
        assert parse_result.author, "作者信息为空"

        video_contents = parse_result.contents
        assert video_contents
        video_path = await video_contents[0].video_path()
        assert video_path.exists()
        logger.info(f"{url} | 视频下载成功, 视频{fmt_size(video_path)}")
        logger.success(f"{url} | Acfun 视频解析成功")

    await parse_acfun_url(url)
