def test_ck2dict():
    from nonebot_plugin_resolver2.cookie import ck2dict

    ck = "SESSDATA=1234567890; bili_jct=1234567890; DedeUserID=1234567890; bili_uid=1234567890"
    assert ck2dict(ck) == {
        "SESSDATA": "1234567890",
        "bili_jct": "1234567890",
        "DedeUserID": "1234567890",
        "bili_uid": "1234567890",
    }


def test_keep_zh_en_num():
    from nonebot_plugin_resolver2.utils import keep_zh_en_num

    assert keep_zh_en_num("12#¥%……*3ab#*#@c测#**@@试") == "123abc测试"
