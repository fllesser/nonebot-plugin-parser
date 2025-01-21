import re
import httpx

from nonebot.plugin import on_message
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, MessageSegment

from .filter import is_not_in_disable_group
from .utils import get_file_seg
from .preprocess import r_keywords, R_KEYWORD_KEY, R_EXTRACT_KEY
from ..constant import COMMON_HEADER
from ..download.common import download_audio
from ..config import NICKNAME

# NCM获取歌曲信息链接
NETEASE_API_CN = "https://www.markingchen.ink"

# NCM临时接口
NETEASE_TEMP_API = (
    "https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?id={}&br=7&type=json"
)

ncm = on_message(rule=is_not_in_disable_group & r_keywords("music.163.com", "163cn.tv"))


@ncm.handle()
async def _(bot: Bot, state: T_State):
    text, keyword = state.get(R_EXTRACT_KEY), state.get(R_KEYWORD_KEY)
    # 解析短链接
    if keyword == "163cn.tv":
        if match := re.search(r"(http:|https:)\/\/163cn\.tv\/([a-zA-Z0-9]+)", text):
            url = match.group(0)
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, follow_redirects=True)
        url = str(resp.url)
    else:
        url = text
    if match := re.search(r"id=(\d+)", url):
        ncm_id = match.group(1)
    else:
        await ncm.finish(f"{NICKNAME}解析 | 网易云 - 获取链接失败")

    # 对接临时接口
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{NETEASE_TEMP_API.replace('{}', ncm_id)}", headers=COMMON_HEADER
            )
        ncm_vip_data = resp.json()
        ncm_music_url, ncm_cover, ncm_singer, ncm_title = (
            ncm_vip_data.get(key) for key in ["music_url", "cover", "singer", "title"]
        )
    except Exception as e:
        await ncm.finish(f"{NICKNAME}解析 | 网易云 - 错误: {e}")
    await ncm.send(
        f"{NICKNAME}解析 | 网易云 - {ncm_title} {ncm_singer}"
        + MessageSegment.image(ncm_cover)
    )
    # 下载音频文件后会返回一个下载路径
    try:
        audio_path = await download_audio(ncm_music_url)
    except Exception as e:
        await ncm.finish(f"音频下载失败 {e}")
    # 发送语音
    await ncm.send(MessageSegment.record(audio_path))
    # 发送群文件
    await ncm.send(
        get_file_seg(
            audio_path, f"{ncm_title}-{ncm_singer}.{audio_path.name.split('.')[-1]}"
        )
    )
