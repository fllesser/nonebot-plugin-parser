import asyncio

from nonebot import logger
from nonebot.exception import FinishedException
import pytest


@pytest.mark.asyncio
async def test_ncm():
    from nonebot_plugin_resolver2.download import download_audio
    from nonebot_plugin_resolver2.parsers import NCMParser

    parser = NCMParser()

    urls = [
        "https://st.music.163.com/listen-together/multishare/index.html?roomId=5766146a1616391e83da2c195811fb07_1744109168288&inviterUid=1868906482",
        "https://music.163.com/song?id=1948109333",
    ]

    async def test_parse_ncm(url: str) -> None:
        logger.info(f"{url} | 开始解析网易云音乐")
        try:
            result = await parser.parse_ncm(url)
            logger.debug(f"{url} | result: {result}")
        except FinishedException:
            logger.warning(f"{url} | 解析失败")
            return

        # 下载音频
        assert result.audio_url
        audio_path = await download_audio(result.audio_url)
        assert audio_path
        logger.debug(audio_path)
        logger.success(f"{url} | 网易云音乐解析成功")

    await asyncio.gather(*[test_parse_ncm(url) for url in urls])
