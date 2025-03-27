from nonebot.log import logger
import pytest


@pytest.mark.asyncio
async def test_weibo_pics():
    from nonebot_plugin_resolver2.download import download_imgs_without_raise, download_video
    from nonebot_plugin_resolver2.parsers.weibo import WeiBo

    weibo = WeiBo()
    urls = [
        "https://video.weibo.com/show?fid=1034:5145615399845897",
        "https://weibo.com/7207262816/P5kWdcfDe",
        "https://weibo.com/7207262816/O70aCbjnd",
        "http://m.weibo.cn/status/5112672433738061",
    ]
    for url in urls:
        logger.info(f"开始解析 {url}")
        video_info = await weibo.parse_share_url(url)
        logger.info(f"解析结果: {video_info}")
        assert video_info.video_url or video_info.images
        logger.success(f"微博解析成功 {url}")
        if video_info.video_url:
            file = await download_video(video_info.video_url)
            assert file
            logger.success(f"微博视频下载成功 {url}")
        if video_info.images:
            files = await download_imgs_without_raise(video_info.images)
            assert len(files) == len(video_info.images)
            logger.success(f"微博图片下载成功 {url}")
