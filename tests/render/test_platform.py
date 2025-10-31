def test_platform_enum():
    from nonebot_plugin_parser.constants import PlatformEnum
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    assert PlatformEnum.bilibili == "bilibili"
    assert str(PlatformEnum.bilibili) == "bilibili"
    assert _COMMON_RENDERER.platform_logos[PlatformEnum.bilibili] is not None
    assert _COMMON_RENDERER.platform_logos[str(PlatformEnum.bilibili)] is not None
