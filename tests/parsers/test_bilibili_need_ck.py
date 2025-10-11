import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_favlist():
    from nonebot_plugin_parser.parsers import BilibiliParser

    logger.info("开始解析B站收藏夹 https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create")
    # https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create
    fav_id = 311147541
    bilibili_parser = BilibiliParser()
    parse_result = await bilibili_parser.parse_favlist(fav_id)

    assert parse_result.title, "标题为空"
    assert parse_result.author, "作者为空"
    avatar_path = await parse_result.author.get_avatar_path()
    assert avatar_path, "头像不存在"
    assert avatar_path.exists(), "头像不存在"

    assert parse_result.contents, "内容为空"
    for content in parse_result.graphics_contents:
        path = await content.get_path()
        assert path.exists(), "内容不存在"
        assert content.text, "文本为空"

    logger.success("B站收藏夹解析成功")


async def test_video():
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.utils import encode_video_to_h264

    parser = BilibiliParser()

    try:
        logger.info("开始解析B站视频 BV1584y167sD p40")
        parse_result = await parser.parse_video(bvid="BV1584y167sD", page_num=40)
        logger.debug(parse_result)
        logger.success("B站视频 BV1584y167sD p40 解析成功")
    except Exception:
        pytest.skip("B站视频 BV1584y167sD p40 解析失败(风控)")

    video_path = await parse_result.video_contents[0].get_path()

    video_h264_path = await encode_video_to_h264(video_path)
    assert video_h264_path.exists()


async def test_merge_av_h264():
    from nonebot_plugin_parser.config import pconfig
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.utils import merge_av_h264

    parser = BilibiliParser()

    try:
        logger.info("开始解析B站视频 av605821754 p41")
        video_url, audio_url = await parser.get_download_urls(avid=605821754, page_index=41)
        logger.debug(f"video_url: {video_url}, audio_url: {audio_url}")
        logger.success("B站视频 av605821754 p41 解析成功")
    except Exception:
        pytest.skip("B站视频 av605821754 p41 解析失败(风控)")

    file_name = "av605821754-41"
    video_path = pconfig.cache_dir / f"{file_name}.mp4"

    assert audio_url is not None

    v_path, a_path = await asyncio.gather(
        DOWNLOADER.streamd(video_url, file_name=f"{file_name}-video.m4s", ext_headers=parser.headers),
        DOWNLOADER.streamd(audio_url, file_name=f"{file_name}-audio.m4s", ext_headers=parser.headers),
    )

    await merge_av_h264(v_path=v_path, a_path=a_path, output_path=video_path)
    assert video_path.exists()


async def test_encode_h264_video():
    import asyncio

    from nonebot_plugin_parser.config import pconfig
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.utils import encode_video_to_h264, merge_av

    try:
        bvid = "BV1VLk9YDEzB"
        parser = BilibiliParser()
        video_url, audio_url = await parser.get_download_urls(bvid=bvid)
        assert video_url is not None
        assert audio_url is not None
        v_path, a_path = await asyncio.gather(
            DOWNLOADER.streamd(video_url, file_name=f"{bvid}-video.m4s", ext_headers=parser.headers),
            DOWNLOADER.streamd(audio_url, file_name=f"{bvid}-audio.m4s", ext_headers=parser.headers),
        )
    except Exception:
        pytest.skip("B站视频 BV1VLk9YDEzB 下载失败")

    video_path = pconfig.cache_dir / f"{bvid}.mp4"
    await merge_av(v_path=v_path, a_path=a_path, output_path=video_path)
    video_h264_path = await encode_video_to_h264(video_path)
    assert not video_path.exists()
    assert video_h264_path.exists()


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

    bilibili_parser = BilibiliParser()

    video_url, _ = await bilibili_parser.get_download_urls(bvid="BV1gRjMziELt")

    logger.debug(f"video_url: {video_url}")
