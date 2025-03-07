import pytest
from nonebot.log import logger

#   bilibili:
# - https://b23.tv/YTg9oSw
# - https://bili2233.cn/rnrwIyU
# - https://www.bilibili.com/video/BV1VLk9YDEzB
# - https://bilibili.com/av1234567
# - https://bilibili.com/BV1uCzoYEEir
# - BV1uCzoYEEir
# - av113706574811958


async def test_bilibili_live():
    from nonebot_plugin_resolver2.parsers.bilibili import parse_live

    # https://live.bilibili.com/23585383
    room_id = 23585383
    title, cover, _ = await parse_live(room_id)
    logger.info(title)
    assert title
    logger.info(cover)
    assert cover.startswith("https://i0.hdslb.com/")


async def test_bilibili_read():
    from nonebot_plugin_resolver2.parsers.bilibili import parse_read

    # https://www.bilibili.com/read/cv523868
    read_id = 523868
    texts, urls = await parse_read(read_id)
    logger.info(texts)
    assert texts
    logger.info(urls)
    assert urls


async def test_bilibili_opus():
    from nonebot_plugin_resolver2.parsers.bilibili import parse_opus

    # - https://www.bilibili.com/opus/998440765151510535
    # - https://www.bilibili.com/opus/1040093151889457152
    opus_ids = [998440765151510535, 1040093151889457152]
    for opus_id in opus_ids:
        urls, orig_text = await parse_opus(opus_id)
        logger.info(urls)
        assert urls
        logger.info(orig_text)
        assert orig_text


@pytest.mark.asyncio
async def test_bilibili_favlist():
    from nonebot_plugin_resolver2.parsers.bilibili import parse_favlist

    # https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create
    fav_id = 311147541
    texts, urls = await parse_favlist(fav_id)
    logger.info(texts)
    assert texts
    logger.info(urls)
    assert urls
