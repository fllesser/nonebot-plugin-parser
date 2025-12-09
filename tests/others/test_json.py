from nonebot import logger

raw_json_list = [
    r'{"ver":"1.0.0.19","prompt":"[QQ小程序]知更鸟\"嚯嗬嗬嗬\"一分三十秒","config":{"type":"normal","width":0,"height":0,"forward":1,"autoSize":0,"ctime":1765215301,"token":"4e4207c3575de312d564485ef8bca3c2"},"needShareCallBack":false,"app":"com.tencent.miniapp_01","view":"view_8C8E89B49BE609866298ADDFF2DBABA4","meta":{"detail_1":{"appid":"1109937557","appType":0,"title":"哔哩哔哩","desc":"知更鸟\"嚯嗬嗬嗬\"一分三十秒","icon":"http:\/\/miniapp.gtimg.cn\/public\/appicon\/432b76be3a548fc128acaa6c1ec90131_200.jpg","preview":"https:\/\/qq.ugcimg.cn\/v1\/qej8dn3qu4uotg40nmf4i8hrojgsa3j4q29gfatprhchvicdtjs7pm73ssa1u0viva7b53mknonj35e1j1i8r8bjaanh9jpfnssa80ad4bippj957qrcoahq2c15i244\/e9vf2tsqr6j29hl2kodb3vahlc","url":"m.q.qq.com\/a\/s\/2772670a8856a28502ba7d366c65d44f","scene":1036,"host":{"uin":3244135150,"nick":"叶落空归"},"shareTemplateId":"8C8E89B49BE609866298ADDFF2DBABA4","shareTemplateData":{},"qqdocurl":"https:\/\/b23.tv\/S9DodEM?share_medium=android&share_source=qq&bbid=XU86759815712638B65E070E6267AB0BEBD4C&ts=1765215299243","showLittleTail":"","gamePoints":"","gamePointsUrl":"","shareOrigin":0}}}',
]

url_list = [
    "https://b23.tv/S9DodEM?share_medium=android&share_source=qq&bbid=XU86759815712638B65E070E6267AB0BEBD4C&ts=1765215299243",
]


def test_std_json():
    import json

    # 直接解析
    for raw_json_str in raw_json_list:
        json.loads(raw_json_str)


def test_msgspec_json_decode():
    from msgspec import json

    for raw_json_str in raw_json_list:
        json.decode(raw_json_str)


def test_parse_json_card():
    from nonebot_plugin_alconna import Hyper

    from nonebot_plugin_parser.matchers.rule import _extract_url

    for i, raw_json_str in enumerate(raw_json_list):
        hyper = Hyper(format="json", raw=raw_json_str)
        url = _extract_url(hyper)
        logger.info(f"extract url from raw json: {url}")
        assert url == url_list[i]
