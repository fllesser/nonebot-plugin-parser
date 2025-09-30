from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_parse():
    from nonebot_plugin_resolver2.download import DOWNLOADER
    from nonebot_plugin_resolver2.download.utils import fmt_size
    from nonebot_plugin_resolver2.parsers import AcfunParser

    url = "https://www.acfun.cn/v/ac46593564"
    acfun_parser = AcfunParser()

    async def parse_acfun_url(url: str) -> None:
        logger.info(f"{url} | 开始解析 Acfun 视频")
        parse_result = await acfun_parser.parse_url(url)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")

        assert parse_result.title, "视频标题为空"
        assert parse_result.author, "作者信息为空"
        assert parse_result.video_url, "视频链接为空"

        logger.info(f"{url} | 开始下载视频")
        video_path = await DOWNLOADER.download_video(parse_result.video_url, ext_headers=acfun_parser.headers)
        assert video_path.exists()
        logger.info(f"{url} | 视频下载成功, 视频{fmt_size(video_path)}")
        logger.success(f"{url} | Acfun 视频解析成功")

    await parse_acfun_url(url)
