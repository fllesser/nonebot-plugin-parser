import asyncio

from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_kugou():
    from nonebot_plugin_resolver2.download import download_audio
    from nonebot_plugin_resolver2.parsers import KuGouParser

    parser = KuGouParser()

    urls = ["https://t3.kugou.com/song.html?id=AeZ3f7EqV2"]

    async def parse_kugou(url: str) -> None:
        logger.info(f"{url} | 开始解析酷狗音乐")

        result = await parser.parse_share_url(url)
        logger.debug(f"{url} | result: {result}")

        # 下载音频
        assert result.audio_url
        audio_path = await download_audio(result.audio_url)
        assert audio_path
        logger.success(f"{url} | 网易云音乐解析成功")

    await asyncio.gather(*[parse_kugou(url) for url in urls])


async def test_kugou_audio_url():
    from nonebot_plugin_resolver2.parsers import KuGouParser

    parser = KuGouParser()

    audio_url = await parser.get_audio_url("1hfw6baEmV3")
    assert audio_url
    logger.success(f"酷狗音乐音频URL: {audio_url}")
