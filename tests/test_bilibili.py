import asyncio
import re

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_bilibili_live():
    logger.info("开始解析B站直播 https://live.bilibili.com/6")
    from nonebot_plugin_resolver2.parsers import BilibiliParser

    # https://live.bilibili.com/6
    room_id = 6
    bilibili_parser = BilibiliParser()
    title, cover, _ = await bilibili_parser.parse_live(room_id)
    assert title
    logger.debug(f"title: {title}")

    assert cover.startswith("https://i0.hdslb.com/")
    logger.debug(f"cover: {cover}")
    logger.success("B站直播解析成功")


@pytest.mark.asyncio
async def test_bilibili_read():
    logger.info("开始解析B站图文 https://www.bilibili.com/read/cv523868")
    from nonebot_plugin_resolver2.parsers import BilibiliParser

    # https://www.bilibili.com/read/cv523868
    read_id = 523868
    bilibili_parser = BilibiliParser()
    texts, urls = await bilibili_parser.parse_read(read_id)
    assert texts
    logger.debug(f"texts: {texts}")

    assert urls
    logger.debug(f"urls: {urls}")
    logger.success("B站图文解析成功")


@pytest.mark.asyncio
async def test_bilibili_opus():
    from nonebot_plugin_resolver2.download import download_imgs_without_raise
    from nonebot_plugin_resolver2.parsers import BilibiliParser

    opus_urls = [
        "https://www.bilibili.com/opus/998440765151510535",
        "https://www.bilibili.com/opus/1040093151889457152",
    ]

    bilibili_parser = BilibiliParser()

    async def test_parse_opus(opus_url: str) -> None:
        matched = re.search(r"opus/(\d+)", opus_url)
        assert matched
        opus_id = int(matched.group(1))
        logger.info(f"{opus_url} | 开始解析哔哩哔哩动态 opus_id: {opus_id}")

        pic_urls, orig_text = await bilibili_parser.parse_opus(opus_id)
        assert pic_urls
        logger.debug(f"{opus_url} | pic_urls: {pic_urls}")

        files = await download_imgs_without_raise(pic_urls)
        assert len(files) == len(pic_urls)

        assert orig_text
        logger.debug(f"{opus_url} | original_text: {orig_text}")

    await asyncio.gather(*[test_parse_opus(opus_url) for opus_url in opus_urls])
    logger.success("B站动态解析成功")
