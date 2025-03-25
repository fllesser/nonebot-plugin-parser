from nonebot.log import logger
import pytest


@pytest.mark.asyncio
async def test_weibo_pics():
    from nonebot_plugin_resolver2.download import download_img
    from nonebot_plugin_resolver2.parsers.weibo import WeiBo

    ext_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
        "referer": "https://weibo.com/",
    }

    weibo = WeiBo()
    # - https://weibo.com/7207262816/P5kWdcfDe
    # - https://weibo.com/7207262816/O70aCbjnd
    # - http://m.weibo.cn/status/5112672433738061
    urls = [
        "https://video.weibo.com/show?fid=1034:5145615399845897",
        "https://weibo.com/7207262816/P5kWdcfDe",
        "https://weibo.com/7207262816/O70aCbjnd",
        "http://m.weibo.cn/status/5112672433738061",
    ]
    for url in urls:
        logger.info(f"开始解析 {url}")
        video_info = await weibo.parse_share_url(url)
        # if video_info.video_url:
        #     # 下载视频
        #     video_path = await download_video(video_info.video_url, ext_headers=ext_headers)
        #     logger.info(f"视频下载成功 {video_path}")
        if video_info.images:
            # 下载图片
            for image in video_info.images:
                logger.info(f"开始下载图片 {image}")
                image_path = await download_img(image, ext_headers=ext_headers)
                logger.info(f"图片下载成功 {image_path}")
