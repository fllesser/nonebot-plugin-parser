def test_platform_enum():
    from nonebot_plugin_parser.renders import CommonRenderer
    from nonebot_plugin_parser.constants import PlatformEnum

    assert PlatformEnum.BILIBILI == "bilibili"
    assert str(PlatformEnum.BILIBILI) == "bilibili"
    assert CommonRenderer.platform_logos[PlatformEnum.BILIBILI] is not None
    assert CommonRenderer.platform_logos[str(PlatformEnum.BILIBILI)] is not None
