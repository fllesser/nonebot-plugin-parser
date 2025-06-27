import asyncio

from nonebot import logger
import pytest
from utils import skip_on_failure


@pytest.mark.asyncio
@skip_on_failure
async def test_douyin_common_video():
    """
    测试普通视频
    https://v.douyin.com/iDHWnyTP
    https://www.douyin.com/video/7440422807663660328
    """
    from nonebot_plugin_resolver2.parsers import DouyinParser

    douyin_parser = DouyinParser()

    common_urls = [
        "https://v.douyin.com/iDHWnyTP",
        "https://www.douyin.com/video/7440422807663660328",
    ]

    async def test_parse_share_url(url: str) -> None:
        logger.info(f"{url} | 开始解析抖音视频")
        video_info = await douyin_parser.parse_share_url(url)
        logger.debug(f"{url} | title: {video_info.title}")
        assert video_info.title
        logger.debug(f"{url} | author: {video_info.author}")
        assert video_info.author
        logger.debug(f"{url} | cover_url: {video_info.cover_url}")
        assert video_info.cover_url
        logger.debug(f"{url} | video_url: {video_info.video_url}")
        assert video_info.video_url
        logger.success(f"{url} | 抖音视频解析成功")

    await asyncio.gather(*[test_parse_share_url(url) for url in common_urls])


@pytest.mark.asyncio
@skip_on_failure
async def test_douyin_old_video():
    """
    老视频，网页打开会重定向到 m.ixigua.com
    https://v.douyin.com/iUrHrruH
    """

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
async def test_douyin_note():
    """
    测试普通图文
    https://www.douyin.com/note/7469411074119322899
    https://v.douyin.com/iP6Uu1Kh
    """
    from nonebot_plugin_resolver2.parsers import DouyinParser

    douyin_parser = DouyinParser()

    note_urls = [
        "https://www.douyin.com/note/7469411074119322899",
        "https://v.douyin.com/iP6Uu1Kh",
        "https://v.douyin.com/LBbstVV4vVg/",
    ]

    async def test_parse_share_url(url: str) -> None:
        logger.info(f"{url} | 开始解析抖音图文")
        video_info = await douyin_parser.parse_share_url(url)
        logger.debug(f"{url} | title: {video_info.title}")
        assert video_info.title
        logger.debug(f"{url} | author: {video_info.author}")
        assert video_info.author
        logger.debug(f"{url} | cover_url: {video_info.cover_url}")
        assert video_info.cover_url
        logger.debug(f"{url} | images: {video_info.pic_urls}")
        assert video_info.pic_urls
        logger.success(f"{url} | 抖音图文解析成功")

    await asyncio.gather(*[test_parse_share_url(url) for url in note_urls])


@pytest.mark.asyncio
@skip_on_failure
async def test_douyin_slides():
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
    video_info = await douyin_parser.parse_share_url(dynamic_image_url)
    logger.debug(f"title: {video_info.title}")
    assert video_info.title
    logger.debug(f"dynamic_images: {video_info.dynamic_urls}")
    assert video_info.dynamic_urls
    logger.success(f"抖音图集(含视频解析出视频)解析成功 {dynamic_image_url}")

    logger.info(f"开始解析抖音图集(含视频解析出静态图片) {static_image_url}")
    video_info = await douyin_parser.parse_share_url(static_image_url)
    logger.debug(f"title: {video_info.title}")
    assert video_info.title
    logger.debug(f"images: {video_info.pic_urls}")
    assert video_info.pic_urls
    logger.success(f"抖音图集(含视频解析出静态图片)解析成功 {static_image_url}")


@pytest.mark.asyncio
@skip_on_failure
async def test_douyin_oversea():
    import httpx

    from nonebot_plugin_resolver2.constant import IOS_HEADER

    url = "https://m.douyin.com/share/note/7484675353898667274"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=IOS_HEADER)
        # headers
        # logger.debug("headers")
        # for key, value in response.headers.items():
        #     logger.debug(f"{key}: {value}")
        logger.debug(f"status: {response.status_code}")
        response.raise_for_status()
        text = response.text
        assert "window._ROUTER_DATA" in text
        # logger.debug(text)
