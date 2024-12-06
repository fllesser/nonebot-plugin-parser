import re, httpx, aiohttp, json, asyncio

from nonebot import on_keyword, logger
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, MessageEvent, Bot, MessageSegment
from urllib.parse import parse_qs, urlparse

from .filter import is_not_in_disable_group
from .utils import get_video_seg, make_node_segment

from ..constant import COMMON_HEADER
from ..data_source.common import download_video, download_img
from ..config import *

# 小红书下载链接
XHS_REQ_LINK = "https://www.xiaohongshu.com/explore/"

xiaohongshu = on_keyword(keywords={"xiaohongshu.com", "xhslink.com"}, rule = Rule(is_not_in_disable_group))

@xiaohongshu.handle()
async def _(bot: Bot, event: MessageEvent):
    message: str = event.message.extract_plain_text().replace("&amp;", "&").strip()
    if match := re.search(r"(http:|https:)\/\/(xhslink|(www\.)xiaohongshu).com\/[A-Za-z\d._?%&+\-=\/#@]*",message):
        msg_url = match.group(0)
    # 请求头
    headers = {
                  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                            'application/signed-exchange;v=b3;q=0.9',
                  'cookie': rconfig.r_xhs_ck,
              } | COMMON_HEADER
    if "xhslink" in msg_url:
        async with httpx.AsyncClient() as client:
            resp = await client.get(msg_url, headers=headers, follow_redirects=True)
            msg_url = str(resp.url)
    # ?: 非捕获组
    pattern = r'(?:/explore/|/discovery/item/|source=note&noteId=)(\w+)'
    if match := re.search(pattern, msg_url):
        xhs_id = match.group(1)
    else:
        return
    # 解析 URL 参数
    parsed_url = urlparse(msg_url)
    params = parse_qs(parsed_url.query)
    # 提取 xsec_source 和 xsec_token
    xsec_source = params.get('xsec_source', [None])[0] or "pc_feed"
    xsec_token = params.get('xsec_token', [None])[0]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f'{XHS_REQ_LINK}{xhs_id}?xsec_source={xsec_source}&xsec_token={xsec_token}', headers=headers)
        html = resp.text
    pattern = r'window.__INITIAL_STATE__=(.*?)</script>'
    if match := re.search(pattern, html):
        json_str = match.group(1)
    else:
        await xiaohongshu.finish("小红书 cookie 可能已失效")
    json_str = json_str.replace("undefined", "null")
    json_obj = json.loads(json_str)
    note_data = json_obj['note']['noteDetailMap'][xhs_id]['note']
    type = note_data['type']
    note_title = note_data['title']
    note_desc = note_data['desc']
    await xiaohongshu.send(Message(
        f"{NICKNAME}解析 | 小红书 - {note_title}\n{note_desc}"))

    aio_task = []
    if type == 'normal':
        image_list = note_data['imageList']
        # 批量下载
        async with aiohttp.ClientSession() as session:
            for index, item in enumerate(image_list):
                aio_task.append(asyncio.create_task(
                    download_img(item['urlDefault'], img_name=f'{index}.jpg', session=session)))
            links_path = await asyncio.gather(*aio_task)
    elif type == 'video':
        # 这是一条解析有水印的视频
        logger.info(note_data['video'])
        video_url = note_data['video']['media']['stream']['h264'][0]['masterUrl']
        # ⚠️ 废弃，解析无水印视频video.consumer.originVideoKey
        # video_url = f"http://sns-video-bd.xhscdn.com/{note_data['video']['consumer']['originVideoKey']}"
        video_name = await download_video(video_url)

        await xiaohongshu.finish(await get_video_seg(video_name))
    # 发送图片
    segs = make_node_segment(bot.self_id, [MessageSegment.image(plugin_cache_dir / img) for img in links_path])
    # 发送异步后的数据
    await xiaohongshu.finish(segs)


