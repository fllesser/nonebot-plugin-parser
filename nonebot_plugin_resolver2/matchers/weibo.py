import math
import re

import aiohttp
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.plugin.on import on_keyword
from nonebot.rule import Rule

from nonebot_plugin_resolver2.config import NICKNAME
from nonebot_plugin_resolver2.constant import COMMON_HEADER
from nonebot_plugin_resolver2.download import download_imgs_without_raise, download_video
from nonebot_plugin_resolver2.parsers.weibo import WeiBo

from .filter import is_not_in_disabled_groups
from .utils import get_video_seg, send_segments

# WEIBO_SINGLE_INFO
WEIBO_SINGLE_INFO = "https://m.weibo.cn/statuses/show?id={}"
weibo_parser = WeiBo()

weibo = on_keyword(keywords={"weibo.com", "m.weibo.cn"}, rule=Rule(is_not_in_disabled_groups))


@weibo.handle()
async def _(bot: Bot, event: MessageEvent):
    message = event.message.extract_plain_text().strip()
    share_prefix = f"{NICKNAME}解析 | 微博 - "
    # fid
    if match := re.search(r"https://video\.weibo\.com/show\?fid=[^\s]+", message):
        video_info = await weibo_parser.parse_share_url(match.group())
        await weibo.send(f"{share_prefix}{video_info.title} - {video_info.author.name}")
        await weibo.finish(await get_video_seg(url=video_info.video_url))

    # https://m.weibo.cn/detail/4976424138313924
    if match := re.search(r"m\.weibo\.cn(?:/detail|/status)?/([A-Za-z\d]+)", message):
        weibo_id = match.group(1)
    # https://weibo.com/tv/show/1034:5007449447661594?mid=5007452630158934
    elif match := re.search(r"mid=([A-Za-z\d]+)", message):
        weibo_id = mid2id(match.group(1))
    # https://weibo.com/1707895270/5006106478773472
    elif match := re.search(r"(?<=weibo.com/)[A-Za-z\d]+/([A-Za-z\d]+)", message):
        weibo_id = match.group(1)
    # 无法获取到id则返回失败信息
    else:
        await weibo.finish(f"{share_prefix}失败：无法获取到微博的 id")

    headers = {
        "accept": "application/json",
        "cookie": "_T_WM=40835919903; WEIBOCN_FROM=1110006030; MLOGIN=0; XSRF-TOKEN=4399c8",
        "Referer": f"https://m.weibo.cn/detail/{weibo_id}",
        **COMMON_HEADER,
    }

    # 请求数据
    async with aiohttp.ClientSession() as session:
        async with session.get(WEIBO_SINGLE_INFO.format(weibo_id), headers=headers) as resp:
            if resp.status != 200:
                await weibo.finish(f"{share_prefix}获取数据失败 {resp.status} {resp.reason}")
            if "application/json" not in resp.headers.get("content-type", ""):
                await weibo.finish(f"{share_prefix}获取数据失败 content-type is not application/json")
            resp = await resp.json()

    weibo_data = resp["data"]
    text, status_title, source, region_name, pics, page_info = (
        weibo_data.get(key)
        for key in [
            "text",
            "status_title",
            "source",
            "region_name",
            "pics",
            "page_info",
        ]
    )
    # 发送消息
    await weibo.send(
        f"{share_prefix}{re.sub(r'<[^>]+>', '', text)}\n{status_title}\n{source}\t{region_name if region_name else ''}"
    )
    if pics:
        pics = [x["large"]["url"] for x in pics]
        image_paths = await download_imgs_without_raise(pics)
        # 发送图片
        segs = [MessageSegment.image(img_path) for img_path in image_paths]
        # 发送异步后的数据
        await send_segments(weibo, segs)
        await weibo.finish()

    if page_info:
        video_url: str = page_info.get("urls", {"mp4_720p_mp4": ""}).get("mp4_720p_mp4", "") or page_info.get(
            "urls", {"mp4_hd_mp4", ""}
        ).get("mp4_hd_mp4", "")
        if not video_url:
            return
        ext_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
            "referer": "https://weibo.com/",
        }
        video_path = await download_video(
            video_url,
            ext_headers=ext_headers,
        )
        await weibo.finish(await get_video_seg(video_path))


# 定义 base62 编码字符表
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base62_encode(number):
    """将数字转换为 base62 编码"""
    if number == 0:
        return "0"

    result = ""
    while number > 0:
        result = ALPHABET[number % 62] + result
        number //= 62

    return result


def mid2id(mid):
    mid = str(mid)[::-1]  # 反转输入字符串
    size = math.ceil(len(mid) / 7)  # 计算每个块的大小
    result = []

    for i in range(size):
        # 对每个块进行处理并反转
        s = mid[i * 7 : (i + 1) * 7][::-1]
        # 将字符串转为整数后进行 base62 编码
        s = base62_encode(int(s))
        # 如果不是最后一个块并且长度不足4位，进行左侧补零操作
        if i < size - 1 and len(s) < 4:
            s = "0" * (4 - len(s)) + s
        result.append(s)

    result.reverse()  # 反转结果数组
    return "".join(result)  # 将结果数组连接成字符串
