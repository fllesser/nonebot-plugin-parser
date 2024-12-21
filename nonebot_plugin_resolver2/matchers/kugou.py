import os
import re
import json
import httpx
import asyncio

from nonebot import on_keyword
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    Bot,
    MessageSegment
)
from .utils import get_file_seg
from .filter import is_not_in_disable_group

from ..data_source.common import download_audio
from ..data_source.common import download_audio
from ..constant import COMMON_HEADER
from ..config import NICKNAME

# KG临时接口
KUGOU_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_kugouSQ.php?msg={}&n=1&type=json"

kugou = on_keyword(
    keywords={"kugou.com"},
    rule = Rule(is_not_in_disable_group)
)

@kugou.handle()
async def _(bot: Bot, event: MessageEvent):
    message = event.message.extract_plain_text().strip()
    # logger.info(message)
    reg1 = r"https?://.*?kugou\.com.*?(?=\s|$|\n)"
    reg2 = r'jumpUrl":\s*"(https?:\\/\\/[^"]+)"'
    reg3 = r'jumpUrl":\s*"(https?://[^"]+)"'
    # 处理卡片问题
    if 'com.tencent.structmsg' in message:
        if match := re.search(reg2, message):
            get_url = match.group(1)
        else:
            if match := re.search(reg3, message):
                get_url = match.group(1)
            else:
                await kugou.send(Message(f"{NICKNAME}解析 | 酷狗音乐 - 获取链接失败"))
                get_url = None
                return
        if get_url:
            url = json.loads('"' + get_url + '"')
    else:
        match = re.search(reg1, message)
        url = match.group()

        # 使用 httpx 获取 URL 的标题
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
    if response.status_code != 200:
        await kugou.finish(f"{NICKNAME}解析 | 酷狗音乐 - 获取链接失败")
    title = response.text
    get_name = r"<title>(.*?)_高音质在线试听"
    if name := re.search(get_name, title):
        kugou_title = name.group(1)  # 只输出歌曲名和歌手名的部分
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{KUGOU_TEMP_API.replace('{}', kugou_title)}", headers=COMMON_HEADER)
            kugou_vip_data = resp.json()
        # logger.info(kugou_vip_data)
        kugou_url = kugou_vip_data.get('music_url')
        kugou_cover = kugou_vip_data.get('cover')
        kugou_name = kugou_vip_data.get('title')
        kugou_singer = kugou_vip_data.get('singer')
        await kugou.send(
            f'{NICKNAME}解析 | 酷狗音乐 - 歌曲：{kugou_name}-{kugou_singer}'
            + MessageSegment.image(kugou_cover)
        )
        # 下载音频文件后会返回一个下载路径
        audio_path = await download_audio(kugou_url)
        # 发送语音
        await kugou.send(MessageSegment.record(audio_path))
        # 发送群文件
        await kugou.finish(get_file_seg(audio_path, f'{kugou_name}-{kugou_singer}.{file_name.split(".")[-1]}'))
    else:
        await kugou.send(f"{NICKNAME}解析 | 酷狗音乐 - 不支持当前外链，请重新分享再试")

        
