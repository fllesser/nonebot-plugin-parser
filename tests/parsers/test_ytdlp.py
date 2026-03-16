import pytest

TIKTOK_URL = "https://www.tiktok.com/@maligoshik/video/7472584144510373125"


@pytest.mark.asyncio
async def test_extract_video_info():
    from nonebot_plugin_parser.download import YTDLP_DOWNLOADER

    await YTDLP_DOWNLOADER.extract_video_info(TIKTOK_URL)


@pytest.mark.asyncio
async def test_download_video():
    from nonebot_plugin_parser.download import YTDLP_DOWNLOADER

    video_path = await YTDLP_DOWNLOADER.download_video(TIKTOK_URL)

    assert video_path.exists()


@pytest.mark.asyncio
async def test_download_audio():
    from nonebot_plugin_parser.download import YTDLP_DOWNLOADER

    url = "https://www.tiktok.com/@fdznews/video/7575810064078884116?is_from_webapp=1&sender_device=pc"

    audio_path = await YTDLP_DOWNLOADER.download_audio(url)

    assert audio_path.exists()


@pytest.mark.asyncio
async def test_download_img():
    from nonebot_plugin_parser.parsers import TikTokParser

    parser = TikTokParser()
    keyword, matched = parser.search_url(TIKTOK_URL)
    result = await parser.parse(keyword, matched)

    assert result.title
    assert result.author
    assert result.contents

    await result.ensure_downloads_complete(img_only=True)
