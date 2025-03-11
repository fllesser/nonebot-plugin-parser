from nonebot.log import logger
import pytest


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
    logger.success("B站直播解析成功")


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
    logger.success("B站图文解析成功")


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
    logger.success("B站动态解析成功")


@pytest.mark.asyncio
async def test_bilibili_favlist():
    logger.info("开始解析B站收藏夹 https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create")
    from nonebot_plugin_resolver2.parsers.bilibili import parse_favlist

    # https://space.bilibili.com/396886341/favlist?fid=311147541&ftype=create
    fav_id = 311147541
    texts, urls = await parse_favlist(fav_id)
    logger.debug(texts)
    assert texts
    logger.debug(urls)
    assert urls
    logger.success("B站收藏夹解析成功")


# @pytest.mark.asyncio
# async def test_re_encode_video():
#     import asyncio
#     from pathlib import Path

#     from bilibili_api import HEADERS

#     from nonebot_plugin_resolver2.download.common import download_file_by_stream, merge_av, re_encode_video
#     from nonebot_plugin_resolver2.parsers.bilibili import parse_video_download_url

#     bvid = "BV1VLk9YDEzB"
#     video_url, audio_url = await parse_video_download_url(bvid=bvid)
#     v_path, a_path = await asyncio.gather(
#         download_file_by_stream(video_url, f"{bvid}-video.m4s", ext_headers=HEADERS),
#         download_file_by_stream(audio_url, f"{bvid}-audio.m4s", ext_headers=HEADERS),
#     )

#     video_path = Path(__file__).parent / f"{bvid}.mp4"
#     await merge_av(v_path, a_path, video_path)
#     video_h264_path = await re_encode_video(video_path)
#     assert not video_path.exists()
#     assert video_h264_path.exists()
