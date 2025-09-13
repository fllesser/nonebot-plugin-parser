import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    """测试快手视频解析"""
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.download.utils import fmt_size
    from nonebot_plugin_resolver2.parsers import KuaishouParser

    parser = KuaishouParser()

    test_urls = [
        "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",
        "https://v.kuaishou.com/2yAnzeZ",  # 视频
        "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc",  # 视频
    ]

    async def parse(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")

        parse_result = await parser.parse_url(url)

        logger.debug(f"{url} | 解析结果: \n{parse_result}")
        assert parse_result.title, "视频标题为空"

        if video_url := parse_result.video_url:
            video_path = await DOWNLOADER.download_video(video_url, ext_headers=parser.v_headers)
            assert video_path.exists()
            logger.debug(f"{url} | 视频下载完成: {video_path}, 视频{fmt_size(video_path)}")

        # 下载图片
        if pic_urls := parse_result.pic_urls:
            img_paths = await DOWNLOADER.download_imgs_without_raise(pic_urls, ext_headers=parser.v_headers)
            logger.debug(f"{url} | 图片下载完成: {img_paths}")
            assert len(img_paths) == len(pic_urls), "图片下载数量不一致"

        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[parse(url) for url in test_urls])
