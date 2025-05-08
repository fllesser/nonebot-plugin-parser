import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_weibo_pics():
    from nonebot_plugin_resolver2.download import download_imgs_without_raise, download_video
    from nonebot_plugin_resolver2.parsers import WeiBoParser

    weibo_parser = WeiBoParser()

    ext_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
        "referer": "https://weibo.com/",
    }
    urls = [
        "https://video.weibo.com/show?fid=1034:5145615399845897",
        "https://weibo.com/7207262816/P5kWdcfDe",
        "https://weibo.com/7207262816/O70aCbjnd",
        "http://m.weibo.cn/status/5112672433738061",
        "https://m.weibo.cn/status/5155768539808352",
    ]

    async def test_parse_share_url(url: str) -> None:
        logger.info(f"{url} | 开始解析微博")
        video_info = await weibo_parser.parse_share_url(url)
        logger.debug(f"{url} | 解析结果: {video_info}")
        assert video_info.video_url or video_info.pic_urls
        logger.success(f"{url} | 微博解析成功")
        if video_info.video_url:
            await download_video(video_info.video_url, ext_headers=ext_headers)
            logger.success(f"{url} | 微博视频下载成功")
        if video_info.pic_urls:
            files = await download_imgs_without_raise(video_info.pic_urls, ext_headers=ext_headers)
            assert len(files) == len(video_info.pic_urls)
            logger.success(f"{url} | 微博图片下载成功")

    await asyncio.gather(*[test_parse_share_url(url) for url in urls])
