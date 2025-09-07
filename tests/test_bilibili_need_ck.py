from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_bilibili_favlist():
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.parsers import BilibiliParser

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


@pytest.mark.asyncio
async def test_bilibili_video():
    import asyncio

    from nonebot_plugin_resolver2.config import plugin_cache_dir
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.download.utils import merge_av
    from nonebot_plugin_resolver2.parsers import BilibiliParser

    try:
        logger.info("开始解析B站视频 BV1VLk9YDEzB")
        parser = BilibiliParser()
        video_info = await parser.parse_video_info(bvid="BV1VLk9YDEzB")
        logger.debug(video_info)
        logger.success("B站视频 BV1VLk9YDEzB 解析成功")

        logger.info("开始解析B站视频 BV1584y167sD p40")
        video_info = await parser.parse_video_info(bvid="BV1584y167sD", page_num=40)
        logger.debug(video_info)
        logger.success("B站视频 BV1584y167sD p40 解析成功")

        logger.info("开始解析B站视频 av605821754 p40")
        video_info = await parser.parse_video_info(avid=605821754, page_num=40)
        logger.debug(video_info)
        logger.success("B站视频 av605821754 p40 解析成功")

        file_name = "BV1584y167sD-40"
        video_path = plugin_cache_dir / f"{file_name}.mp4"
        video_url = video_info.video_url

        if audio_url := video_info.audio_url:
            v_path, a_path = await asyncio.gather(
                DOWNLOADER.streamd(video_url, file_name=f"{file_name}-video.m4s", ext_headers=parser.headers),
                DOWNLOADER.streamd(audio_url, file_name=f"{file_name}-audio.m4s", ext_headers=parser.headers),
            )
            await merge_av(v_path=v_path, a_path=a_path, output_path=video_path)
        else:
            video_path = await DOWNLOADER.streamd(video_url, file_name=f"{file_name}.mp4", ext_headers=parser.headers)

        assert video_path.exists()
    except Exception:
        pytest.skip("B站视频 BV1584y167sD p40 下载失败")


async def test_encode_h264_video():
    import asyncio

    from bilibili_api import HEADERS

    from nonebot_plugin_resolver2.config import plugin_cache_dir
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.download.utils import encode_video_to_h264, merge_av
    from nonebot_plugin_resolver2.parsers import BilibiliParser

    try:
        bvid = "BV1VLk9YDEzB"
        bilibili_parser = BilibiliParser()
        video_url, audio_url = await bilibili_parser.parse_video_download_url(bvid=bvid)
        assert video_url is not None
        assert audio_url is not None
        v_path, a_path = await asyncio.gather(
            DOWNLOADER.streamd(video_url, file_name=f"{bvid}-video.m4s", ext_headers=HEADERS),
            DOWNLOADER.streamd(audio_url, file_name=f"{bvid}-audio.m4s", ext_headers=HEADERS),
        )
    except Exception:
        pytest.skip("B站视频 BV1VLk9YDEzB 下载失败")

    video_path = plugin_cache_dir / f"{bvid}.mp4"
    await merge_av(v_path=v_path, a_path=a_path, output_path=video_path)
    video_h264_path = await encode_video_to_h264(video_path)
    assert not video_path.exists()
    assert video_h264_path.exists()


@pytest.mark.asyncio
async def test_no_audio_video():
    from nonebot_plugin_resolver2.parsers import BilibiliParser

    bilibili_parser = BilibiliParser()

    video_url, _ = await bilibili_parser.parse_video_download_url(bvid="BV1gRjMziELt")

    logger.debug(f"video_url: {video_url}")
