import pytest


async def test_get_video_info():
    from nonebot_plugin_resolver2.download.ytdlp import get_video_info

    url = "https://youtu.be/NiHF-cwto_A?si=Eho8a8AO9c1347Uj"

    try:
        video_info = await get_video_info(url)
    except Exception:
        pytest.skip("获取 youtube 视频信息失败")

    assert video_info is not None
    assert video_info.get("title") is not None


async def test_download_video():
    from nonebot_plugin_resolver2.download.ytdlp import ytdlp_download_video

    url = "https://youtu.be/NiHF-cwto_A?si=Eho8a8AO9c1347Uj"

    try:
        video_path = await ytdlp_download_video(url)
    except Exception:
        pytest.skip("下载 youtube 视频失败")

    assert video_path is not None
    assert video_path.exists()


async def test_download_audio():
    from nonebot_plugin_resolver2.download.ytdlp import ytdlp_download_audio

    url = "https://youtu.be/NiHF-cwto_A?si=Eho8a8AO9c1347Uj"

    try:
        audio_path = await ytdlp_download_audio(url)
    except Exception:
        pytest.skip("下载 youtube 音频失败")

    assert audio_path is not None
    assert audio_path.exists()
