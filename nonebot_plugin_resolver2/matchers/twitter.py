import re

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment
from nonebot import logger

from .filter import resolve_filter
from .utils import get_video_seg, make_node_segment, send_forward_both
from ..constant import COMMON_HEADER, GENERAL_REQ_LINK
from ..core.common import download_img, download_video
from ..core.request import fetch_data

from ..config import *

twitter = on_regex(
    r"(x.com)", priority=1
)

@twitter.handle()
@resolve_filter
async def _(bot: Bot, event: Event):
    """
        X解析
    :param bot:
    :param event:
    :return:
    """
    msg: str = str(event.message).strip()
    segs: list = []
    if match := re.search(r"https?:\/\/x.com\/[0-9-a-zA-Z_]{1,20}\/status\/([0-9]*)", msg):
        x_url = match.group(0)
    x_url = GENERAL_REQ_LINK.replace("{}", x_url)

    headers = {
            'Accept': 'ext/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Host': '47.99.158.118',
            'Proxy-Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-User': '?1'
        }
    try:
        x_data: object = await fetch_data(x_url, headers=headers).json()['data']
    except Exception as e:
        for i in range(4):
            x_data = await fetch_data(f'{x_url}/photo/{i}', headers=headers).json()['data']
            x_url_res = x_data['url']
            if x_url_res.endswith(".jpg") or x_url_res.endswith(".png"):
                res = await download_img(x_url_res, '', PROXY)
                segs.append(MessageSegment.image(f"file://{res}"))
    segs.append(f"{NICKNAME}解析 | X")
    if x_data:
        video_path = await download_video(x_url_res, PROXY)
        segs.append(await get_video_seg(video_path))
    await send_forward_both(bot, event, make_node_segment(bot.self_id, segs))

