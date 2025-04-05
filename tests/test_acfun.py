from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse_acfun_url():
    from nonebot_plugin_resolver2.parsers.acfun import download_acfun_video, parse_acfun_url

    urls = ["https://www.acfun.cn/v/ac46593564", "https://www.acfun.cn/v/ac40867941"]
    for url in urls:
        acid = int(url.split("/")[-1].split("ac")[1])
        logger.info(f"开始解析 acfun 视频 {acid}")
        m3u8s_url, video_desc = await parse_acfun_url(url)
        assert m3u8s_url
        assert video_desc
        logger.debug(f"m3u8s_url: {m3u8s_url}, video_desc: {video_desc}")

        logger.info(f"开始下载 acfun 视频 {acid}")
        video_file = await download_acfun_video(m3u8s_url, acid)
        assert video_file
        logger.info(f"acfun 视频 {acid} 下载成功, 文件大小: {video_file.stat().st_size / 1024 / 1024:.2f} MB")
