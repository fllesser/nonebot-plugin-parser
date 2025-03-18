import re

import aiohttp
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.plugin import on_message

from nonebot_plugin_resolver2.config import NEED_UPLOAD, NICKNAME
from nonebot_plugin_resolver2.constant import COMMON_HEADER
from nonebot_plugin_resolver2.download import download_audio
from nonebot_plugin_resolver2.download.utils import keep_zh_en_num

from .filter import is_not_in_disabled_groups
from .preprocess import ExtractText, Keyword, r_keywords
from .utils import get_file_seg

# NCM获取歌曲信息链接
NETEASE_API_CN = "https://www.markingchen.ink"

# NCM临时接口
NETEASE_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?id={}&br=7&type=json"

ncm = on_message(rule=is_not_in_disabled_groups & r_keywords("music.163.com", "163cn.tv"))


@ncm.handle()
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    share_prefix = f"{NICKNAME}解析 | 网易云 - "
    # 解析短链接
    url: str = ""
    if keyword == "163cn.tv":
        if match := re.search(r"(http:|https:)\/\/163cn\.tv\/([a-zA-Z0-9]+)", text):
            url = match.group(0)
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=False) as resp:
                    url = resp.headers.get("Location", "")
    else:
        url = text
    if match := re.search(r"id=(\d+)", url):
        ncm_id = match.group(1)
    else:
        await ncm.finish(f"{share_prefix}获取链接失败")

    # 对接临时接口
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{NETEASE_TEMP_API.replace('{}', ncm_id)}", headers=COMMON_HEADER) as resp:
                ncm_vip_data = await resp.json()
        ncm_music_url, ncm_cover, ncm_singer, ncm_title = (
            ncm_vip_data.get(key) for key in ["music_url", "cover", "singer", "title"]
        )
    except Exception as e:
        await ncm.finish(f"{share_prefix}错误: {e}")
    await ncm.send(f"{share_prefix}{ncm_title} {ncm_singer}" + MessageSegment.image(ncm_cover))
    # 下载音频文件后会返回一个下载路径
    try:
        audio_path = await download_audio(ncm_music_url)
    except Exception:
        await ncm.send("音频下载失败，请联系机器人管理员", reply_message=True)
        raise
    # 发送语音
    await ncm.send(MessageSegment.record(audio_path))
    # 发送群文件
    if NEED_UPLOAD:
        file_name = keep_zh_en_num(f"{ncm_title}-{ncm_singer}")
        file_name = f"{file_name}.flac"
        await ncm.send(get_file_seg(audio_path, file_name))
