import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_favlist():
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.parsers import BilibiliParser

    logger.info("开始解析B站收藏夹 https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create")
    # https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create
    fav_id = 311147541
    bilibili_parser = BilibiliParser()
    texts, urls = await bilibili_parser.parse_favlist(fav_id)

    assert texts
    logger.debug(texts)

    assert urls
    logger.debug(urls)

    files = await DOWNLOADER.download_imgs_without_raise(urls)
    assert len(files) == len(urls)
    logger.success("B站收藏夹解析成功")


async def test_video():
    from nonebot_plugin_parser.config import plugin_cache_dir
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

    file_name = "BV1584y167sD-40"
    video_path = plugin_cache_dir / f"{file_name}.mp4"

    video_h264_path = await encode_video_to_h264(video_path)
    assert video_h264_path.exists()


async def test_merge_av_h264():
    from nonebot_plugin_parser.config import plugin_cache_dir
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.utils import merge_av_h264

    parser = BilibiliParser()

    try:
        logger.info("开始解析B站视频 av605821754 p41")
        video_url, audio_url = await parser.parse_video_download_url(avid=605821754, page_index=41)
        logger.debug(f"video_url: {video_url}, audio_url: {audio_url}")
        logger.success("B站视频 av605821754 p41 解析成功")
    except Exception:
        pytest.skip("B站视频 av605821754 p41 解析失败(风控)")

    file_name = "av605821754-41"
    video_path = plugin_cache_dir / f"{file_name}.mp4"

    assert audio_url is not None

    v_path, a_path = await asyncio.gather(
        DOWNLOADER.streamd(video_url, file_name=f"{file_name}-video.m4s", ext_headers=parser.headers),
        DOWNLOADER.streamd(audio_url, file_name=f"{file_name}-audio.m4s", ext_headers=parser.headers),
    )

    await merge_av_h264(v_path=v_path, a_path=a_path, output_path=video_path)
    assert video_path.exists()


async def test_encode_h264_video():
    import asyncio

    from nonebot_plugin_parser.config import plugin_cache_dir
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.utils import encode_video_to_h264, merge_av

    try:
        bvid = "BV1VLk9YDEzB"
        parser = BilibiliParser()
        video_url, audio_url = await parser.parse_video_download_url(bvid=bvid)
        assert video_url is not None
        assert audio_url is not None
        v_path, a_path = await asyncio.gather(
            DOWNLOADER.streamd(video_url, file_name=f"{bvid}-video.m4s", ext_headers=parser.headers),
            DOWNLOADER.streamd(audio_url, file_name=f"{bvid}-audio.m4s", ext_headers=parser.headers),
        )
    except Exception:
        pytest.skip("B站视频 BV1VLk9YDEzB 下载失败")

    video_path = plugin_cache_dir / f"{bvid}.mp4"
    await merge_av(v_path=v_path, a_path=a_path, output_path=video_path)
    video_h264_path = await encode_video_to_h264(video_path)
    assert not video_path.exists()
    assert video_h264_path.exists()


async def test_max_size_video():
    from nonebot_plugin_parser.download import DOWNLOADER
    from nonebot_plugin_parser.exception import DownloadSizeLimitException
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()
    bvid = "BV1du4y1E7Nh"
    try:
        _, audio_url = await parser.parse_video_download_url(bvid=bvid)
    except DownloadSizeLimitException:
        pytest.skip("解析B站视频 BV1du4y1E7Nh 失败(风控)")

    assert audio_url is not None

    try:
        await DOWNLOADER.download_audio(audio_url, ext_headers=parser.headers)
    except DownloadSizeLimitException:
        pass


@pytest.mark.asyncio
async def test_no_audio_video():
    from nonebot_plugin_parser.parsers import BilibiliParser

    bilibili_parser = BilibiliParser()

    video_url, _ = await bilibili_parser.parse_video_download_url(bvid="BV1gRjMziELt")

    logger.debug(f"video_url: {video_url}")
