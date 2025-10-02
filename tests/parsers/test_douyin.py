import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_common_video():
    """测试普通视频"""
    from nonebot_plugin_resolver2.parsers import DouyinParser

    parser = DouyinParser()

    common_urls = [
        "https://v.douyin.com/_2ljF4AmKL8/",
        "https://www.douyin.com/video/7521023890996514083",
    ]

    async def test_parse_share_url(url: str) -> None:
        logger.info(f"{url} | 开始解析抖音视频")
        parse_result = await parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title
        assert parse_result.author
        assert parse_result.extra.get("cover_path")
        assert parse_result.video_paths
        logger.success(f"{url} | 抖音视频解析成功")

    await asyncio.gather(*[test_parse_share_url(url) for url in common_urls])


@pytest.mark.asyncio
async def test_old_video():
    """老视频，网页打开会重定向到 m.ixigua.com"""

    # from nonebot_plugin_resolver2.parsers.douyin import DouYin

    # parser = DouYin()
    # # 该作品已删除，暂时忽略
    # url = "https://v.douyin.com/iUrHrruH"
    # logger.info(f"开始解析抖音西瓜视频 {url}")
    # video_info = await parser.parse_share_url(url)
    # logger.debug(f"title: {video_info.title}")
    # assert video_info.title
    # logger.debug(f"author: {video_info.author}")
    # assert video_info.author
    # logger.debug(f"cover_url: {video_info.cover_url}")
    # assert video_info.cover_url
    # logger.debug(f"video_url: {video_info.video_url}")
    # assert video_info.video_url
    # logger.success(f"抖音西瓜视频解析成功 {url}")


@pytest.mark.asyncio
async def test_note():
    """测试普通图文"""
    from nonebot_plugin_resolver2.parsers import DouyinParser

    parser = DouyinParser()

    note_urls = [
        "https://www.douyin.com/note/7469411074119322899",
        "https://v.douyin.com/iP6Uu1Kh",
    ]

    async def test_parse_share_url(url: str) -> None:
        logger.info(f"{url} | 开始解析抖音图文")
        parse_result = await parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title
        assert parse_result.author
        assert parse_result.img_paths
        logger.success(f"{url} | 抖音图文解析成功")

    await asyncio.gather(*[test_parse_share_url(url) for url in note_urls])


@pytest.mark.asyncio
async def test_slides():
    """
    含视频的图集
    https://v.douyin.com/CeiJfqyWs # 将会解析出视频
    https://www.douyin.com/note/7450744229229235491 # 解析成普通图片
    """
    from nonebot_plugin_resolver2.parsers import DouyinParser

    douyin_parser = DouyinParser()

    dynamic_image_url = "https://v.douyin.com/CeiJfqyWs"
    static_image_url = "https://www.douyin.com/note/7450744229229235491"

    logger.info(f"开始解析抖音图集(含视频解析出视频) {dynamic_image_url}")
    parse_result = await douyin_parser.parse_share_url(dynamic_image_url)
    logger.debug(f"{dynamic_image_url} | 解析结果: \n{parse_result}")
    assert parse_result.title
    assert parse_result.dynamic_paths
    logger.success(f"抖音图集(含视频解析出视频)解析成功 {dynamic_image_url}")

    logger.info(f"开始解析抖音图集(含视频解析出静态图片) {static_image_url}")
    parse_result = await douyin_parser.parse_share_url(static_image_url)
    logger.debug(f"{static_image_url} | 解析结果: \n{parse_result}")
    assert parse_result.title
    assert parse_result.img_paths
    logger.success(f"抖音图集(含视频解析出静态图片)解析成功 {static_image_url}")
