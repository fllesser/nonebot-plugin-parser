def test_platform_enum():
    from nonebot_plugin_parser.constants import PlatformEnum
    from nonebot_plugin_parser.renders.common import assets

    assets.ensure_resources()
    assert PlatformEnum.BILIBILI == "bilibili"
    assert str(PlatformEnum.BILIBILI) == "bilibili"
    assert assets.PLATFORM_LOGOS[PlatformEnum.BILIBILI] is not None
    assert assets.PLATFORM_LOGOS[str(PlatformEnum.BILIBILI)] is not None
