async def test_ck2dict():
    from nonebot_plugin_resolver2.cookie import ck2dict

    ck = "SESSDATA=1234567890; bili_jct=1234567890; DedeUserID=1234567890; bili_uid=1234567890"
    assert ck2dict(ck) == {
        "SESSDATA": "1234567890",
        "bili_jct": "1234567890",
        "DedeUserID": "1234567890",
        "bili_uid": "1234567890",
    }
