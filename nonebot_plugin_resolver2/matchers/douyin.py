import re
import httpx
import aiohttp

from nonebot import on_keyword, logger
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment

from .utils import get_video_seg, send_forward_both, make_node_segment
from .filter import is_not_in_disable_group
from ..data_source.tiktok import generate_x_bogus_url
from ..constant import DOUYIN_VIDEO, DY_TOUTIAO_INFO, URL_TYPE_CODE_DICT
from ..constant import COMMON_HEADER

from ..config import *

douyin = on_keyword(keywords={"v.douyin.com"}, rule = Rule(is_not_in_disable_group))

@douyin.handle()
async def _(bot: Bot, event: Event) -> None:
    """
        抖音解析
    :param bot:
    :param event:
    :return:
    """
    # 消息
    msg: str = str(event.message).strip()
    logger.info(msg)
    # 正则匹配
    reg = r"(http:|https:)\/\/v.douyin.com\/[A-Za-z\d._?%&+\-=#]*"
    dou_url = re.search(reg, msg, re.I)[0]
    dou_url_2 = httpx.get(dou_url).headers.get('location')
    # logger.error(dou_url_2)
    reg2 = r".*(video|note)\/(\d+)\/(.*?)"
    # 获取到ID
    dou_id = re.search(reg2, dou_url_2, re.I)[2]
    # logger.info(dou_id)
    # 如果没有设置dy的ck就结束，因为获取不到
    douyin_ck = rconfig.r_douyin_ck
    if douyin_ck == "":
        logger.error(rconfig)
        await douyin.send(Message(f"{NICKNAME}解析 | 抖音，无法获取到管理员设置的抖音ck！"))
        return
    # API、一些后续要用到的参数
    headers = {
                  'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                  'referer': f'https://www.douyin.com/video/{dou_id}',
                  'cookie': douyin_ck
              } | COMMON_HEADER
    api_url = DOUYIN_VIDEO.replace("{}", dou_id)
    api_url = generate_x_bogus_url(api_url, headers)  # 如果请求失败直接返回
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers, timeout=10) as response:
            detail = await response.json()
            if detail is None:
                await douyin.send(Message(f"{NICKNAME}解析 | 抖音，解析失败！"))
                return
            # 获取信息
            detail = detail['aweme_detail']
            # 判断是图片还是视频
            url_type_code = detail['aweme_type']
            url_type = URL_TYPE_CODE_DICT.get(url_type_code, 'video')
            await douyin.send(Message(f"{NICKNAME}解析 | 抖音，{detail.get('desc')}"))
            # 根据类型进行发送
            if url_type == 'video':
                # 解析播放地址
                player_uri = detail.get("video").get("play_addr")['uri']
                player_real_addr = DY_TOUTIAO_INFO.replace("{}", player_uri)
                # 发送视频
                # logger.info(player_addr)
                # await douyin.send(Message(MessageSegment.video(player_addr)))
                await douyin.send(await get_video_seg(url = player_real_addr))
            elif url_type == 'image':
                # 无水印图片列表/No watermark image list
                no_watermark_image_list = []
                # 有水印图片列表/With watermark image list
                # watermark_image_list = []
                # 遍历图片列表/Traverse image list
                for i in detail['images']:
                    # 无水印图片列表
                    no_watermark_image_list.append(MessageSegment.image(i['url_list'][0]))
                    # 有水印图片列表
                    # watermark_image_list.append(i['download_url_list'][0])
                await send_forward_both(bot, event, make_node_segment(bot.self_id, no_watermark_image_list))


