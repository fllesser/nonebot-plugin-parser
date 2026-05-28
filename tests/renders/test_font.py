from nonebot import logger


def test_font():
    from nonebot_plugin_parser.renders.common import assets

    assets.ensure_resources()
    metrics = assets.FONTS.body.metrics
    chars = ["中", "A", "1", "a", ",", "。"]
    for char in chars:
        logger.info(f"{char}: {metrics.get_char_width(char)}")
    for char in range(128):
        char = chr(char)
        logger.info(f"{char}: {metrics.get_char_width(char)}")


def test_cjk_width():
    from nonebot_plugin_parser.renders.common import assets

    assets.ensure_resources()
    metrics = assets.FONTS.name.metrics
    count = 0
    for char_ord in range(ord("\u4e00"), ord("\u9fff")):
        char = chr(char_ord)
        width = metrics.get_char_width(char)
        if width != metrics.cjk_width:
            # logger.warning(f"{char}({char_ord}): {width} != {metrics.cjk_width}")
            count += 1
    cjk_count = ord("\u9fff") - ord("\u4e00") + 1
    logger.info(f"CJK 字符数: {cjk_count}，不等于 CJK 宽度的字符数: {count}，占比: {count / cjk_count:.2%}")
