import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_live():
    logger.info("开始解析B站直播 https://live.bilibili.com/6")
    from nonebot_plugin_parser.parsers import BilibiliParser

    url = "https://live.bilibili.com/1"
    parser = BilibiliParser()
    try:
        result = await parser.parse_live(url)
    except Exception as e:
        pytest.skip(f"B站直播解析失败: {e} (风控)")

    logger.debug(f"result: {result}")
    assert result.title, "标题为空"
    assert result.author, "作者为空"

    avatar_path = await result.author.get_avatar_path()
    assert avatar_path, "头像不存在"
    assert avatar_path.exists(), "头像不存在"

    img_contents = result.img_contents
    for img_content in img_contents:
        path = await img_content.get_path()
        assert path.exists(), "图片不存在"

    logger.success("B站直播解析成功")


@pytest.mark.asyncio
async def test_read():
    logger.info("开始解析B站图文 https://www.bilibili.com/read/cv523868")
    from nonebot_plugin_parser.parsers import BilibiliParser

    url = "https://www.bilibili.com/read/cv523868"
    bilibili_parser = BilibiliParser()
    result = await bilibili_parser.parse_read(url)
    logger.debug(f"result: {result}")
    assert result.title, "标题为空"
    assert result.author, "作者为空"
    avatar_path = await result.author.get_avatar_path()
    assert avatar_path, "头像不存在"
    assert avatar_path.exists(), "头像不存在"

    assert result.contents, "内容为空"
    for content in result.contents:
        path = await content.get_path()
        assert path.exists(), "内容不存在"

    logger.success("B站图文解析成功")


@pytest.mark.asyncio
async def test_opus():
    from nonebot_plugin_parser.parsers import BilibiliParser

    opus_urls = [
        "https://www.bilibili.com/opus/998440765151510535",
        "https://www.bilibili.com/opus/1040093151889457152",
    ]

    parser = BilibiliParser()

    async def test_parse_opus(opus_url: str) -> None:
        try:
            result = await parser.parse_opus(opus_url)
        except Exception as e:
            pytest.skip(f"{opus_url} | opus 解析失败: {e} (风控)")

        assert result.contents, "内容为空"
        for content in result.contents:
            path = await content.get_path()
            assert path.exists(), "内容不存在"

        assert result.author, "作者为空"
        avatar_path = await result.author.get_avatar_path()
        assert avatar_path, "头像不存在"
        assert avatar_path.exists(), "头像不存在"

        graphics_contents = result.graphics_contents
        assert graphics_contents, "图文内容为空"

        for graphics_content in graphics_contents:
            path = await graphics_content.get_path()
            assert path.exists(), "图文内容不存在"

    await asyncio.gather(*[test_parse_opus(opus_url) for opus_url in opus_urls])
    logger.success("B站动态解析成功")


async def test_dynamic():
    from nonebot_plugin_parser.parsers import BilibiliParser

    dynamic_urls = ["https://t.bilibili.com/1120105154190770281"]

    parser = BilibiliParser()

    async def test_parse_dynamic(dynamic_url: str) -> None:
        result = await parser.parse_dynamic(dynamic_url)
        assert result.title, "标题为空"
        assert result.author, "作者为空"
        avatar_path = await result.author.get_avatar_path()
        assert avatar_path, "头像不存在"
        assert avatar_path.exists(), "头像不存在"

        img_contents = result.img_contents
        for img_content in img_contents:
            path = await img_content.get_path()
            assert path.exists(), "图片不存在"

    await asyncio.gather(*[test_parse_dynamic(dynamic_url) for dynamic_url in dynamic_urls])
    logger.success("B站动态解析成功")
