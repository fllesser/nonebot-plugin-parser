import os, httpx, re, json, asyncio

from nonebot import on_keyword
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, MessageEvent, Bot, MessageSegment

from .utils import upload_both
from ..data_source.common import download_audio
from ..constant import COMMON_HEADER

from .filter import is_not_in_disable_group
from ..config import *

# KG临时接口
KUGOU_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_kugouSQ.php?msg={}&n=1&type=json"

kugou = on_keyword(keywords={"kugou.com"}, rule = Rule(is_not_in_disable_group))

@kugou.handle()
async def kugou_handler(bot: Bot, event: MessageEvent):
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
    async with httpx.AsyncClient as client:
        response = await client.get(url, follow_redirects=True)
    if response.status_code == 200:
        title = response.text
        get_name = r"<title>(.*?)_高音质在线试听"
        if name := re.search(get_name, title)
            kugou_title = name.group(1)  # 只输出歌曲名和歌手名的部分
            async with httpx.AsyncClient as client:
                kugou_vip_data = await client.get(f"{KUGOU_TEMP_API.replace('{}', kugou_title)}", headers=COMMON_HEADER).json()
            # logger.info(kugou_vip_data)
            kugou_url = kugou_vip_data.get('music_url')
            kugou_cover = kugou_vip_data.get('cover')
            kugou_name = kugou_vip_data.get('title')
            kugou_singer = kugou_vip_data.get('singer')
            await kugou.send(Message(
                [MessageSegment.image(kugou_cover),
                 MessageSegment.text(f'{NICKNAME}解析 | 酷狗音乐 - 歌曲：{kugou_name}-{kugou_singer}')]))
            # 下载音频文件后会返回一个下载路径
            file_name = await download_audio(kugou_url)

            file = store.get_plugin_cache_file(file_name)
            # 发送语音
            await kugou.send(MessageSegment.record(file = file))
            # 发送群文件
            await upload_both(bot, event, file, f'{kugou_name}-{kugou_singer}.{file_name.split(".")[-1]}')
        else:
            await kugou.send(Message(f"{NICKNAME}解析 | 酷狗音乐 - 不支持当前外链，请重新分享再试"))
    else:
        await kugou.send(Message(f"{NICKNAME}解析 | 酷狗音乐 - 获取链接失败"))
