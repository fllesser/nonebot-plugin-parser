from nonebot.log import logger


async def test_douyin_common_video():
    """
    测试普通视频
    https://v.douyin.com/iDHWnyTP
    https://www.douyin.com/video/7440422807663660328
    """
    from nonebot_plugin_resolver2.parsers.douyin import DouYin

    parser = DouYin()

    common_urls = [
        "https://v.douyin.com/iDHWnyTP",
        "https://www.douyin.com/video/7440422807663660328",
    ]
    for url in common_urls:
        video_info = await parser.parse_share_url(url)
        logger.info(video_info)
        assert video_info.video_url is not None


async def test_douyin_note():
    """
    测试普通图文
    https://www.douyin.com/note/7469411074119322899
    https://v.douyin.com/iP6Uu1Kh
    """
    from nonebot_plugin_resolver2.parsers.douyin import DouYin

    parser = DouYin()

    note_urls = [
        "https://www.douyin.com/note/7469411074119322899",
        "https://v.douyin.com/iP6Uu1Kh",
    ]
    for url in note_urls:
        video_info = await parser.parse_share_url(url)
        logger.info(video_info)
        assert video_info.video_url is not None


# - 老视频，网页打开会重定向到 m.ixigua.com
#   - https://v.douyin.com/iUrHrruH
# - 含视频的图集
#   - https://v.douyin.com/CeiJfqyWs # 将会解析出视频
#   - https://www.douyin.com/note/7450744229229235491 # 解析成普通图片
