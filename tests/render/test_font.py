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


def test_cjk_width():
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    font = _COMMON_RENDERER.fontset.name_font
    count = 0
    for char_ord in range(ord("\u4e00"), ord("\u9fff")):
        char = chr(char_ord)
        width = font.get_char_width(char)
        if width != font.cjk_width:
            logger.error(f"{char}({char_ord}): {width} != {font.cjk_width}")
            count += 1
    cjk_count = ord("\u9fff") - ord("\u4e00") + 1
    logger.info(f"CJK 字符数: {cjk_count}，不等于 CJK 宽度的字符数: {count}，占比: {count / cjk_count:.2%}")
