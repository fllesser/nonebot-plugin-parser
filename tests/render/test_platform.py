def test_platform_enum():
    from nonebot_plugin_parser.constants import PlatformEnum
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    assert PlatformEnum.BILIBILI == "bilibili"
    assert str(PlatformEnum.BILIBILI) == "bilibili"
    assert _COMMON_RENDERER.platform_logos[PlatformEnum.BILIBILI] is not None
    assert _COMMON_RENDERER.platform_logos[str(PlatformEnum.BILIBILI)] is not None
