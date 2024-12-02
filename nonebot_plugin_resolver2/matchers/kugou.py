import os, httpx, re, json

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment

from .utils import upload_both
from ..core.common import download_audio
from ..constant import COMMON_HEADER

from .filter import resolve_filter
from ..config import *

# KG临时接口
KUGOU_TEMP_API = "https://www.hhlqilongzhu.cn/api/dg_kugouSQ.php?msg={}&n=1&type=json"

kugou = on_regex(r"(kugou.com)")

@kugou.handle()
@resolve_filter
async def kugou_handler(bot: Bot, event: Event):
    message = str(event.message)
    # logger.info(message)
    reg1 = r"https?://.*?kugou\.com.*?(?=\s|$|\n)"
    reg2 = r'jumpUrl":\s*"(https?:\\/\\/[^"]+)"'
    reg3 = r'jumpUrl":\s*"(https?://[^"]+)"'
    # 处理卡片问题
    if 'com.tencent.structmsg' in message:
        match = re.search(reg2, message)
        if match:
            get_url = match.group(1)
        else:
            match = re.search(reg3, message)
            if match:
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
    response = httpx.get(url, follow_redirects=True)
    if response.status_code == 200:
        title = response.text
        get_name = r"<title>(.*?)_高音质在线试听"
        name = re.search(get_name, title)
        if name:
            kugou_title = name.group(1)  # 只输出歌曲名和歌手名的部分
            kugou_vip_data = httpx.get(f"{KUGOU_TEMP_API.replace('{}', kugou_title)}", headers=COMMON_HEADER).json()
            # logger.info(kugou_vip_data)
            kugou_url = kugou_vip_data.get('music_url')
            kugou_cover = kugou_vip_data.get('cover')
            kugou_name = kugou_vip_data.get('title')
            kugou_singer = kugou_vip_data.get('singer')
            await kugou.send(Message(
                [MessageSegment.image(kugou_cover),
                 MessageSegment.text(f'{NICKNAME}解析 | 酷狗音乐 - 歌曲：{kugou_name}-{kugou_singer}')]))
            # 下载音频文件后会返回一个下载路径
            kugou_music_path = await download_audio(kugou_url)
            # 发送语音
            await kugou.send(Message(MessageSegment.record(kugou_music_path)))
            # 发送群文件
            await upload_both(bot, event, kugou_music_path,
                              f'{kugou_name}-{kugou_singer}.{kugou_music_path.split(".")[-1]}')
            if os.path.exists(kugou_music_path):
                os.unlink(kugou_music_path)
        else:
            await kugou.send(Message(f"{NICKNAME}解析 | 酷狗音乐 - 不支持当前外链，请重新分享再试"))
    else:
        await kugou.send(Message(f"{NICKNAME}解析 | 酷狗音乐 - 获取链接失败"))
