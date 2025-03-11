from nonebot.log import logger


def test_generate_file_name():
    import random

    from nonebot_plugin_resolver2.download.common import generate_file_name

    suffix_lst = [".jpg", ".png", ".gif", ".webp", ".jpeg", ".bmp", ".tiff", ".ico", ".svg", ".heic", ".heif"]
    # 测试 100 个链接
    for i in range(20):
        url = f"https://www.google.com/test{i}{random.choice(suffix_lst)}"
        file_name = generate_file_name(url)
        new_file_name = generate_file_name(url)
        assert file_name == new_file_name
        logger.info(f"{url}: {file_name}")


async def test_re_encode_video():
    import asyncio
    from pathlib import Path

    from bilibili_api import HEADERS

    from nonebot_plugin_resolver2.download.common import download_file_by_stream, merge_av, re_encode_video
    from nonebot_plugin_resolver2.parsers.bilibili import parse_video_download_url

    bvid = "BV1VLk9YDEzB"
    video_url, audio_url = await parse_video_download_url(bvid=bvid)
    v_path, a_path = await asyncio.gather(
        download_file_by_stream(video_url, f"{bvid}-video.m4s", ext_headers=HEADERS),
        download_file_by_stream(audio_url, f"{bvid}-audio.m4s", ext_headers=HEADERS),
    )

    video_path = Path(__file__).parent / f"{bvid}.mp4"
    await merge_av(v_path, a_path, video_path)
    video_h264_path = await re_encode_video(video_path)
    assert not video_path.exists()
    assert video_h264_path.exists()
