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
        logger.info(f"开始解析抖音视频 {url}")
        video_info = await parser.parse_share_url(url)
        logger.debug(f"title: {video_info.title}")
        assert video_info.title
        logger.debug(f"author: {video_info.author}")
        assert video_info.author
        logger.debug(f"cover_url: {video_info.cover_url}")
        assert video_info.cover_url
        logger.debug(f"video_url: {video_info.video_url}")
        assert video_info.video_url
        logger.success(f"抖音视频解析成功 {url}")


async def test_douyin_old_video():
    """
    老视频，网页打开会重定向到 m.ixigua.com
    https://v.douyin.com/iUrHrruH
    """

    # from nonebot_plugin_resolver2.parsers.douyin import DouYin
    # parser = DouYin()
    # 该作品已删除，暂时忽略
    # url = "https://v.douyin.com/iUrHrruH"
    # logger.info(f"开始解析抖音西瓜视频 {url}")
    # video_info = await parser.parse_share_url(url)
    # logger.debug(f"title: {video_info.title}")
    # assert video_info.title
    # logger.debug(f"author: {video_info.author}")
    # assert video_info.author
    # logger.debug(f"cover_url: {video_info.cover_url}")
    # assert video_info.cover_url
    # logger.debug(f"video_url: {video_info.video_url}")
    # assert video_info.video_url
    # logger.success(f"抖音西瓜视频解析成功 {url}")


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
        logger.info(f"开始解析抖音图文 {url}")
        video_info = await parser.parse_share_url(url)
        logger.debug(f"title: {video_info.title}")
        assert video_info.title
        logger.debug(f"author: {video_info.author}")
        assert video_info.author
        logger.debug(f"cover_url: {video_info.cover_url}")
        assert video_info.cover_url
        logger.debug(f"images: {video_info.images}")
        assert video_info.images
        logger.success(f"抖音图文解析成功 {url}")


async def test_douyin_slides():
    """
    含视频的图集
    https://v.douyin.com/CeiJfqyWs # 将会解析出视频
    https://www.douyin.com/note/7450744229229235491 # 解析成普通图片
    """
    from nonebot_plugin_resolver2.parsers.douyin import DouYin

    parser = DouYin()

    dynamic_image_url = "https://v.douyin.com/CeiJfqyWs"
    static_image_url = "https://www.douyin.com/note/7450744229229235491"

    logger.info(f"开始解析抖音图集(含视频解析出视频) {dynamic_image_url}")
    video_info = await parser.parse_share_url(dynamic_image_url)
    logger.debug(f"title: {video_info.title}")
    assert video_info.title
    logger.debug(f"dynamic_images: {video_info.dynamic_images}")
    assert video_info.dynamic_images
    logger.success(f"抖音图集(含视频解析出视频)解析成功 {dynamic_image_url}")

    logger.info(f"开始解析抖音图集(含视频解析出静态图片) {static_image_url}")
    video_info = await parser.parse_share_url(static_image_url)
    logger.debug(f"title: {video_info.title}")
    assert video_info.title
    logger.debug(f"images: {video_info.images}")
    assert video_info.images
    logger.success(f"抖音图集(含视频解析出静态图片)解析成功 {static_image_url}")
