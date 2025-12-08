import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_common_video():
    """测试普通视频"""
    from nonebot_plugin_parser.parsers import DouyinParser
    from nonebot_plugin_parser.exception import DownloadException

    parser = DouyinParser()

    common_urls = [
        "https://v.douyin.com/_2ljF4AmKL8/",
        "https://www.douyin.com/video/7521023890996514083",
    ]

    async def test_parse(url: str) -> None:
        logger.info(f"{url} | 开始解析抖音视频")
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"

        result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{result}")

        assert result.title, "标题为空"
        assert result.author, "作者为空"
        assert await result.cover_path, "封面为空"
        assert result.video_contents, "视频内容为空"

        video_path = await result.video_contents[0].get_path()

        assert video_path.exists(), "视频不存在"
        logger.success(f"{url} | 抖音视频解析成功")

    for url in common_urls:
        try:
            await test_parse(url)
        except DownloadException:
            pytest.skip("抖音视频下载失败, 随机到的 cdn 过期")


@pytest.mark.asyncio
async def test_old_video():
    """老视频，网页打开会重定向到 m.ixigua.com"""

    # from nonebot_plugin_parser.parsers.douyin import DouYin

    # parser = DouYin()
    # # 该作品已删除，暂时忽略
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


@pytest.mark.asyncio
async def test_note():
    """测试普通图文"""
    from nonebot_plugin_parser.parsers import DouyinParser

    parser = DouyinParser()

    note_urls = [
        "https://www.douyin.com/note/7469411074119322899",
        "https://v.douyin.com/iP6Uu1Kh",
    ]

    async def test_parse(url: str) -> None:
        logger.info(f"{url} | 开始解析抖音图文")
        keyword, searched = parser.search_url(url)
        assert searched, "无法匹配 URL"

        result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{result}")
        assert result.title, "标题为空"
        assert result.author, "作者为空"
        if img_contents := result.img_contents:
            for img_content in img_contents:
                path = await img_content.get_path()
                assert path.exists(), "图片不存在"
        logger.success(f"{url} | 抖音图文解析成功")

    for url in note_urls:
        await test_parse(url)


@pytest.mark.asyncio
async def test_slides():
    """
    含视频的图集
    https://v.douyin.com/CeiJfqyWs # 将会解析出视频
    https://www.douyin.com/note/7450744229229235491 # 解析成普通图片
    """
    from nonebot_plugin_parser.parsers import DouyinParser
    from nonebot_plugin_parser.exception import DownloadException

    parser = DouyinParser()

    dynamic_image_url = "https://v.douyin.com/CeiJfqyWs"

    logger.info(f"开始解析抖音图集(含视频解析出视频) {dynamic_image_url}")
    keyword, searched = parser.search_url(dynamic_image_url)
    assert searched, "无法匹配 URL"
    result = await parser.parse(keyword, searched)
    logger.debug(f"{dynamic_image_url} | 解析结果: \n{result}")
    assert result.title, "标题为空"
    dynamic_contents = result.dynamic_contents
    assert dynamic_contents, "动态内容为空"
    for dynamic_content in dynamic_contents:
        try:
            path = await dynamic_content.get_path()
        except DownloadException:
            pytest.skip("抖音动态内容下载失败, 随机到的 cdn 过期")
        assert path.exists(), "动态内容不存在"
    logger.success(f"抖音图集(含视频解析出视频)解析成功 {dynamic_image_url}")

    static_image_url = "https://www.douyin.com/note/7450744229229235491"
    logger.info(f"开始解析抖音图集(含视频解析出静态图片) {static_image_url}")
    keyword, searched = parser.search_url(static_image_url)
    assert searched, "无法匹配 URL"
    result = await parser.parse(keyword, searched)
    logger.debug(f"{static_image_url} | 解析结果: \n{result}")
    assert result.title, "标题为空"
    img_contents = result.img_contents
    assert img_contents, "图片内容为空"
    for img_content in img_contents:
        try:
            path = await img_content.get_path()
        except DownloadException:
            pytest.skip("抖音动态内容下载失败, 随机到的 cdn 过期")
        assert path.exists(), "图片内容不存在"
    logger.success(f"抖音图集(含视频解析出静态图片)解析成功 {static_image_url}")
