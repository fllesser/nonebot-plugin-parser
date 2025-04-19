import re

import aiohttp
from nonebot import logger
from nonebot.exception import FinishedException

from ..exception import ParseException
from .data import COMMON_HEADER, ParseResult
from .utils import get_redirect_url


class NCMParser:
    """
    网易云音乐解析器
    """

    def __init__(self):
        self.short_url_pattern = re.compile(r"(http:|https:)\/\/163cn\.tv\/([a-zA-Z0-9]+)")

    async def parse_ncm(self, ncm_url: str):
        if matched := self.short_url_pattern.search(ncm_url):
            ncm_url = matched.group(0)
            ncm_url = await get_redirect_url(ncm_url)

        # 获取网易云歌曲id
        matched = re.search(r"\?id=(\d+)", ncm_url)
        if not matched:
            logger.warning(f"无效网易云链接: {ncm_url}, 忽略")
            raise FinishedException
        ncm_id = matched.group(1)

        # 对接临时接口
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?id={ncm_id}&br=7&type=json", headers=COMMON_HEADER
                ) as resp:
                    resp.raise_for_status()
                    ncm_vip_data = await resp.json()
            ncm_music_url, ncm_cover, ncm_singer, ncm_title = (
                ncm_vip_data.get(key) for key in ["music_url", "cover", "singer", "title"]
            )
        except Exception as e:
            raise ParseException(f"网易云音乐解析失败: {e}")

        return ParseResult(
            title=ncm_title,
            author=ncm_singer,
            cover_url=ncm_cover,
            audio_url=ncm_music_url,
        )
