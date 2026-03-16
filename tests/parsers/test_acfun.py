import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_parse():
    from nonebot_plugin_parser.parsers import AcfunParser

    # url = "https://www.acfun.cn/v/ac46593564"
    url = "https://www.acfun.cn/v/ac11348130"
    parser = AcfunParser()

    async def parse_acfun_url(url: str) -> None:
        logger.info(f"{url} | 开始解析 Acfun 视频")
        # 使用 patterns 匹配 URL
        keyword, searched = parser.search_url(url)
        assert searched, f"无法匹配 URL: {url}"
        result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{result}")

        assert result.title, "视频标题为空"
        assert result.author, "作者信息为空"
        assert result.video, "视频内容为空"

        await result.ensure_downloads_complete()

        logger.success(f"{url} | Acfun 视频解析成功")

    await parse_acfun_url(url)
