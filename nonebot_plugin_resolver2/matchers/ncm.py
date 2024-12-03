import re
import httpx

from nonebot import on_message
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, MessageEvent, Bot, MessageSegment

from .filter import is_not_in_disable_group
from .utils import *
from ..constant import COMMON_HEADER
from ..data_source.common import download_audio
from ..config import *

# NCM获取歌曲信息链接
NETEASE_API_CN = 'https://www.markingchen.ink'

# NCM临时接口
NETEASE_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?id={}&br=7&type=json"

async def is_ncm(event: MessageEvent) -> bool:
    message = str(event.message).strip()
    return any(key in message for key in {"music.163.com", "163cn.tv"})

ncm = on_message(rule = Rule(is_ncm, is_not_in_disable_group))

@ncm.handle()
async def ncm_handler(bot: Bot, event: MessageEvent):
    message = str(event.message).strip()
    # 解析短链接
    if "163cn.tv" in message:
        message = re.search(r"(http:|https:)\/\/163cn\.tv\/([a-zA-Z0-9]+)", message).group(0)
        message = str(httpx.head(message, follow_redirects=True).url)

    ncm_id = re.search(r"id=(\d+)", message).group(1)
    if ncm_id is None:
        await ncm.finish(f"{NICKNAME}解析 | 网易云 - 获取链接失败")

    # 对接临时接口
    ncm_vip_data = httpx.get(f"{NETEASE_TEMP_API.replace('{}', ncm_id)}", headers=COMMON_HEADER).json()
    ncm_url = ncm_vip_data['music_url']
    ncm_cover = ncm_vip_data['cover']
    ncm_singer = ncm_vip_data['singer']
    ncm_title = ncm_vip_data['title']
    await ncm.send(Message(
        [MessageSegment.image(ncm_cover), MessageSegment.text(f'{NICKNAME}解析 | 网易云音乐 - {ncm_title}-{ncm_singer}')]))
    # 下载音频文件后会返回一个下载路径
    file_name = await download_audio(ncm_url)
    file = plugin_cache_dir / file_name
    # 发送语音
    await ncm.send(Message(MessageSegment.record(file)))
    # 发送群文件
    await upload_both(bot, event, file, f'{ncm_title}-{ncm_singer}.{file_name.split(".")[-1]}')