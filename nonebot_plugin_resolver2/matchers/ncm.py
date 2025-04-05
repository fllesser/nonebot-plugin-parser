import re

import aiohttp
from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import MessageSegment

from ..config import NEED_UPLOAD, NICKNAME
from ..constant import COMMON_HEADER
from ..download import download_audio, download_img
from ..download.utils import keep_zh_en_num
from ..exception import handle_exception
from .filter import is_not_in_disabled_groups
from .helper import get_file_seg, get_img_seg
from .preprocess import ExtractText, Keyword, r_keywords

# NCM获取歌曲信息链接
NETEASE_API_CN = "https://www.markingchen.ink"

# NCM临时接口
NETEASE_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?id={}&br=7&type=json"

ncm = on_message(rule=is_not_in_disabled_groups & r_keywords("music.163.com", "163cn.tv"))


@ncm.handle()
@handle_exception(ncm)
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
    matched = re.search(r"id=(\d+)", url)
    if not matched:
        logger.info(f"{share_prefix}无效链接，忽略 - {text}")
        return
    ncm_id = matched.group(1)

    # 对接临时接口
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{NETEASE_TEMP_API.replace('{}', ncm_id)}", headers=COMMON_HEADER) as resp:
                ncm_vip_data = await resp.json()
        ncm_music_url, ncm_cover, ncm_singer, ncm_title = (
            ncm_vip_data.get(key) for key in ["music_url", "cover", "singer", "title"]
        )
    except Exception as e:
        await ncm.send(f"{share_prefix}错误: {e}")
        raise
    await ncm.send(f"{share_prefix}{ncm_title} {ncm_singer}" + get_img_seg(await download_img(ncm_cover)))
    # 下载音频文件后会返回一个下载路径
    audio_path = await download_audio(ncm_music_url)
    # 发送语音
    await ncm.send(MessageSegment.record(audio_path))
    # 发送群文件
    if NEED_UPLOAD:
        file_name = keep_zh_en_num(f"{ncm_title}-{ncm_singer}")
        file_name = f"{file_name}.flac"
        await ncm.send(get_file_seg(audio_path, file_name))
