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


def test_limited_size_dict():
    from nonebot_plugin_resolver2.download.ytdlp import LimitedSizeDict

    limited_size_dict = LimitedSizeDict()
    for i in range(20):
        limited_size_dict[f"test{i}"] = f"test{i}"
    assert len(limited_size_dict) == 20
    for i in range(20):
        assert limited_size_dict[f"test{i}"] == f"test{i}"
    for i in range(20, 30):
        limited_size_dict[f"test{i}"] = f"test{i}"
    assert len(limited_size_dict) == 20


async def test_ytdlp_download_video():
    from nonebot_plugin_resolver2.download.ytdlp import ytdlp_download_video

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    file_path = await ytdlp_download_video(url)
    assert file_path.exists()
