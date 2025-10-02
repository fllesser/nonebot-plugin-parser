url = "https://www.tiktok.com/@xwc1897/video/7436010419002608928?is_from_webapp=1&sender_device=pc"


async def test_extract_video_info():
    from nonebot_plugin_parser.download import YTDLP_DOWNLOADER

    video_info = await YTDLP_DOWNLOADER.extract_video_info(url)

    assert video_info is not None
    assert video_info.get("title") is not None


async def test_download_video():
    from nonebot_plugin_parser.download import YTDLP_DOWNLOADER

    video_path = await YTDLP_DOWNLOADER.download_video(url)

    assert video_path is not None
    assert video_path.exists()


async def test_download_audio():
    from nonebot_plugin_parser.download import YTDLP_DOWNLOADER

    audio_path = await YTDLP_DOWNLOADER.download_audio(url)

    assert audio_path is not None
    assert audio_path.exists()
