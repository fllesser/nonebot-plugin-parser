import re

import aiohttp

from ..exception import ParseException
from .base import BaseParser, VideoAuthor, VideoInfo


class KuGou(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        """解析酷狗分享链接"""
        # https://t1.kugou.com/song.html?id=1hfw6baEmV3
        async with aiohttp.ClientSession() as session:
            async with session.get(share_url, ssl=False) as response:
                response.raise_for_status()
                html_text = await response.text()
        # <title>土坡上的狗尾草_卢润泽_高音质在线
        matched = re.search(r"<title>(.+)_高音质在线", html_text)
        if not matched:
            raise ParseException("无法获取歌曲名")

        title = matched.group(1).replace("_", " ")

        api_url = f"https://www.hhlqilongzhu.cn/api/dg_kugouSQ.php?msg={title}&n=1&type=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=self.default_headers) as response:
                if response.status != 200:
                    raise ParseException(f"无法获取歌曲信息: {response.status}")
                song_info = await response.json()

        return VideoInfo(
            title=song_info.get("title"),
            cover_url=song_info.get("cover"),
            music_url=song_info.get("music_url"),
            author=VideoAuthor(name=song_info["singer"]),
        )
