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
