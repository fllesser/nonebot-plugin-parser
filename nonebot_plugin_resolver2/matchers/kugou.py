import re
import httpx

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.plugin.on import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from .utils import get_file_seg
from .filter import is_not_in_disable_group
from .preprocess import r_keywords, R_EXTRACT_KEY
from ..download.common import download_audio
from ..constant import COMMON_HEADER
from ..config import NICKNAME

# KG临时接口
KUGOU_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_kugouSQ.php?msg={}&n=1&type=json"

kugou = on_message(rule=is_not_in_disable_group & r_keywords("kugou.com"))


@kugou.handle()
async def _(bot: Bot, state: T_State):
    text = state.get(R_EXTRACT_KEY)
    pattern = r"https?://.*?kugou\.com.*?(?=\s|$|\n)"
    # 处理卡片问题
    if match := re.search(pattern, text):
        url = match.group(0)
    else:
        logger.info(f"无效链接，忽略 - {text}")
        return
    # 使用 httpx 获取 URL 的标题
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
    if response.status_code != 200:
        await kugou.finish(f"{NICKNAME}解析 | 酷狗音乐 - 获取链接失败")
    title = response.text
    pattern = r"<title>(.*?)_高音质在线试听"
    if match := re.search(pattern, title):
        kugou_title = match.group(1)  # 只输出歌曲名和歌手名的部分
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{KUGOU_TEMP_API.replace('{}', kugou_title)}", headers=COMMON_HEADER
            )
            kugou_vip_data = resp.json()
        # logger.info(kugou_vip_data)
        kugou_url = kugou_vip_data.get("music_url")
        kugou_cover = kugou_vip_data.get("cover")
        kugou_name = kugou_vip_data.get("title")
        kugou_singer = kugou_vip_data.get("singer")
        await kugou.send(
            f"{NICKNAME}解析 | 酷狗音乐 - 歌曲：{kugou_name}-{kugou_singer}"
            + MessageSegment.image(kugou_cover)
        )
        # 下载音频文件后会返回一个下载路径
        audio_path = await download_audio(kugou_url)
        # 发送语音
        await kugou.send(MessageSegment.record(audio_path))
        # 发送群文件
        await kugou.finish(
            get_file_seg(
                audio_path,
                f"{kugou_name}-{kugou_singer}.{audio_path.name.split('.')[-1]}",
            )
        )
    else:
        await kugou.send(f"{NICKNAME}解析 | 酷狗音乐 - 不支持当前外链，请重新分享再试")
