from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_bilibili_live():
    logger.info("开始解析B站直播 https://live.bilibili.com/23585383")
    from nonebot_plugin_resolver2.parsers.bilibili import parse_live

    # https://live.bilibili.com/23585383
    room_id = 23585383
    title, cover, _ = await parse_live(room_id)
    assert title
    logger.debug(f"title: {title}")

    assert cover.startswith("https://i0.hdslb.com/")
    logger.debug(f"cover: {cover}")
    logger.success("B站直播解析成功")


@pytest.mark.asyncio
async def test_bilibili_read():
    logger.info("开始解析B站图文 https://www.bilibili.com/read/cv523868")
    from nonebot_plugin_resolver2.parsers.bilibili import parse_read

    # https://www.bilibili.com/read/cv523868
    read_id = 523868
    texts, urls = await parse_read(read_id)
    assert texts
    logger.debug(f"texts: {texts}")

    assert urls
    logger.debug(f"urls: {urls}")
    logger.success("B站图文解析成功")


@pytest.mark.asyncio
async def test_bilibili_opus():
    from nonebot_plugin_resolver2.download import download_imgs_without_raise
    from nonebot_plugin_resolver2.parsers.bilibili import parse_opus

    logger.info(
        "开始解析B站动态 https://www.bilibili.com/opus/998440765151510535, https://www.bilibili.com/opus/1040093151889457152"
    )
    # - https://www.bilibili.com/opus/998440765151510535
    # - https://www.bilibili.com/opus/1040093151889457152
    opus_ids = [998440765151510535, 1040093151889457152]
    for opus_id in opus_ids:
        urls, orig_text = await parse_opus(opus_id)
        assert urls
        logger.debug(urls)

        files = await download_imgs_without_raise(urls)
        assert len(files) == len(urls)

        assert orig_text
        logger.debug(orig_text)
    logger.success("B站动态解析成功")
