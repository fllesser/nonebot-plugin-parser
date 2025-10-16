from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_favlist():
    from nonebot_plugin_parser.parsers import BilibiliParser

    logger.info("开始解析B站收藏夹 https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create")
    # https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create
    fav_id = 311147541
    parser = BilibiliParser()
    result = await parser.parse_favlist(fav_id)

    assert result.title, "标题为空"
    assert result.author, "作者为空"
    avatar_path = await result.author.get_avatar_path()
    assert avatar_path, "头像不存在"
    assert avatar_path.exists(), "头像不存在"

    assert result.contents, "内容为空"
    for content in result.contents:
        path = await content.get_path()
        assert path.exists(), "内容不存在"

    logger.success("B站收藏夹解析成功")


async def test_video():
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()

    try:
        logger.info("开始解析B站视频 BV1584y167sD p40")
        result = await parser.parse_video(bvid="BV1584y167sD", page_num=40)
        logger.debug(result)
        logger.success("B站视频 BV1584y167sD p40 解析成功")
    except Exception:
        pytest.skip("B站视频 BV1584y167sD p40 解析失败(风控)")

    video_path = await result.video_contents[0].get_path()
    assert video_path.exists(), "视频不存在"


async def test_max_size_video():
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.exception import DurationLimitException, SizeLimitException
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()
    bvid = "BV1du4y1E7Nh"
    audio_url = None
    try:
        _, audio_url = await parser.get_download_urls(bvid=bvid)
    except DurationLimitException:
        pass

    assert audio_url is not None
    try:
        await DOWNLOADER.download_audio(audio_url, ext_headers=parser.headers)
    except SizeLimitException:
        pass


@pytest.mark.asyncio
async def test_no_audio_video():
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()

    video_url, audio_url = await parser.get_download_urls(bvid="BV1gRjMziELt")

    assert video_url is not None
    assert audio_url is None
