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
    logger.info("开始解析B站直播 https://live.bilibili.com/23585383")
    from nonebot_plugin_resolver2.parsers.bilibili import parse_live

    # https://live.bilibili.com/23585383
    room_id = 23585383
    title, cover, _ = await parse_live(room_id)
    logger.debug(title)
    assert title
    logger.debug(cover)
    assert cover.startswith("https://i0.hdslb.com/")


async def test_bilibili_read():
    logger.info("开始解析B站图文 https://www.bilibili.com/read/cv523868")
    from nonebot_plugin_resolver2.parsers.bilibili import parse_read

    # https://www.bilibili.com/read/cv523868
    read_id = 523868
    texts, urls = await parse_read(read_id)
    logger.debug(texts)
    assert texts
    logger.debug(urls)
    assert urls


async def test_bilibili_opus():
    logger.info(
        "开始解析B站动态 https://www.bilibili.com/opus/998440765151510535, https://www.bilibili.com/opus/1040093151889457152"
    )
    from nonebot_plugin_resolver2.parsers.bilibili import parse_opus

    # - https://www.bilibili.com/opus/998440765151510535
    # - https://www.bilibili.com/opus/1040093151889457152
    opus_ids = [998440765151510535, 1040093151889457152]
    for opus_id in opus_ids:
        urls, orig_text = await parse_opus(opus_id)
        logger.debug(urls)
        assert urls
        logger.debug(orig_text)
        assert orig_text


@pytest.mark.asyncio
async def test_bilibili_favlist():
    logger.info(
        "开始解析B站收藏夹 https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create"
    )
    from nonebot_plugin_resolver2.parsers.bilibili import parse_favlist

    # https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create
    fav_id = 311147541
    texts, urls = await parse_favlist(fav_id)
    logger.debug(texts)
    assert texts
    logger.debug(urls)
    assert urls
