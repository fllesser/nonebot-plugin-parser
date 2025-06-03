import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_ncm():
    from nonebot_plugin_resolver2.download import download_audio
    from nonebot_plugin_resolver2.parsers import KuGouParser

    parser = KuGouParser()

    urls = ["https://t3.kugou.com/song.html?id=AeZ3f7EqV2"]

    async def test_parse_ncm(url: str) -> None:
        logger.info(f"{url} | 开始解析酷狗音乐")

        result = await parser.parse_share_url(url)
        logger.debug(f"{url} | result: {result}")

        # 下载音频
        assert result.audio_url
        audio_path = await download_audio(result.audio_url)
        assert audio_path
        logger.success(f"{url} | 网易云音乐解析成功")

    await asyncio.gather(*[test_parse_ncm(url) for url in urls])
