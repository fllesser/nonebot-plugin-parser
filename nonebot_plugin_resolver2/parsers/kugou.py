import re
import aiohttp

from .base import BaseParser, VideoAuthor, VideoInfo


class KuGou(BaseParser):
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        # https://t1.kugou.com/song.html?id=1hfw6baEmV3
        async with aiohttp.ClientSession() as session:
            async with session.get(share_url, ssl=False) as response:
                response.raise_for_status()
                html_text = await response.text()
        # 从 html 中获取 hash 值
        # {"hash":"C76E9235868169CABE26D02D521ED90A"
        match = re.search(r'{"hash":"([a-zA-Z0-9]+)"', html_text)
        if not match:
            raise ValueError("无法获取歌曲 hash 值")
        hash_value = match.group(1)
        download_api_url = (
            f"http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={hash_value}"
        )
        # http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash=c76e9235868169cabe26d02d521ed90a
        async with aiohttp.ClientSession() as session:
            async with session.get(
                download_api_url, headers=self.default_headers
            ) as response:
                response.raise_for_status()
                song_info = await response.json(content_type="text/html")
        return VideoInfo(
            cover_url=song_info.get("imgUrl"),
            title=song_info.get("songName"),
            music_url=song_info.get("url"),
            video_url="",
            author=VideoAuthor(name=song_info.get("author_name")),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        return await super().parse_video_id(video_id)
