from nonebot import logger


def test_font():
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    font = _COMMON_RENDERER.fontset.text_font
    chars = ["中", "A", "1", "a", ",", "。"]
    for char in chars:
        logger.info(f"{char}: {font.get_char_width(char)}")
    for char in range(128):
        char = chr(char)
        logger.info(f"{char}: {font.get_char_width(char)}")
