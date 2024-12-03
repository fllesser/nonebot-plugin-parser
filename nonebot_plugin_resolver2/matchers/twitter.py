import re, httpx, asyncio

from nonebot import on_keyword
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, MessageEvent, Bot, MessageSegment
from nonebot import logger

from .filter import is_not_in_disable_group
from .utils import get_video_seg
from ..constant import COMMON_HEADER, GENERAL_REQ_LINK
from ..data_source.common import download_img, download_video

from ..config import *

twitter = on_keyword(keywords={"x.com"}, rule = Rule(is_not_in_disable_group))

@twitter.handle()
async def _(bot: Bot, event: MessageEvent):

    msg: str = event.message.extract_plain_text().strip()

    x_url = re.search(r"https?:\/\/x.com\/[0-9-a-zA-Z_]{1,20}\/status\/([0-9]*)", msg)[0]

    x_url = GENERAL_REQ_LINK.replace("{}", x_url)

    # 内联一个请求
    async def x_req(url):
        async with httpx.AsyncClient() as client:
            return client.get(url, headers={
                'Accept': 'ext/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                          'application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Host': '47.99.158.118',
                'Proxy-Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-User': '?1',
                **COMMON_HEADER
            })
    resp = await x_req(x_url)
    x_data: object = resp.json()['data']

    
    if x_data is None:
        x_url = x_url + '/photo/1'
        resp = await x_req(x_url)
        x_data = resp.json()['data']

    x_url_res = x_data['url']

    await twitter.send(Message(f"{NICKNAME}识别 | X"))

    seg: MessageSegment = None
    # 图片
    if x_url_res.endswith(".jpg") or x_url_res.endswith(".png"):
        img_name = await download_img(url = x_url_res, proxy = PROXY)
        seg = MessageSegment.image(plugin_cache_dir / img_name)
    else:
        # 视频
        video_name = await download_video(x_url_res, proxy=PROXY)
        seg = await get_video_seg(file_name = video_name)
    if seg:
        await twitter.send(seg)
    # logger.info(f"X解析: {x_url}")
    # headers = {
    #         'Accept': 'ext/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
    #                   'application/signed-exchange;v=b3;q=0.7',
    #         'Accept-Encoding': 'gzip, deflate',
    #         'Accept-Language': 'zh-CN,zh;q=0.9',
    #         'Host': '47.99.158.118',
    #         'Proxy-Connection': 'keep-alive',
    #         'Upgrade-Insecure-Requests': '1',
    #         'Sec-Fetch-User': '?1'
    #     }
    # try:
    #     x_data: object = (await fetch_data(x_url, headers=headers)).json()['data']
    # except Exception as e:
    #     for i in range(4):
    #         x_data = (await fetch_data(f'{x_url}/photo/{i}', headers=headers)).json()['data']
    #         x_url_res = x_data['url']
    #         if x_url_res.endswith(".jpg") or x_url_res.endswith(".png"):
    #             res = await download_img(x_url_res, '', PROXY)
    #             segs.append(MessageSegment.image(f"file://{res}"))
    # segs.append(f"{NICKNAME}解析 | X")
    # if x_data:
    #     video_path = await download_video(x_data['url'], PROXY)
    #     segs.append(await get_video_seg(video_path))
    # await send_forward_both(bot, event, make_node_segment(bot.self_id, segs))

