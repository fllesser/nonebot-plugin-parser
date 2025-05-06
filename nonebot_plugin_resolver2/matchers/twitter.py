import re
from typing import Any

import aiohttp
from nonebot import logger, on_keyword
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.rule import Rule

from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg, send_segments
from ..config import NICKNAME, PROXY
from ..constant import COMMON_HEADER
from ..download import download_img, download_video
from ..exception import ParseException, handle_exception

twitter = on_keyword(keywords={"x.com"}, rule=Rule(is_not_in_disabled_groups))


@twitter.handle()
@handle_exception(twitter)
async def _(event: MessageEvent):
    msg: str = event.message.extract_plain_text().strip()
    pattern = r"https?:\/\/x.com\/[0-9-a-zA-Z_]{1,20}\/status\/([0-9]+)"
    matched = re.search(pattern, msg)
    if not matched:
        logger.info("没有匹配到 x.com 的 url, 忽略")
        return
    x_url = matched.group(0)

    await twitter.send(f"{NICKNAME}解析 | 小蓝鸟")

    video_urls, pic_urls = await parse_x_url(x_url)

    segments: list[Message | MessageSegment | str] = []

    # 下载视频
    for video_url in video_urls:
        print(video_url)
        video_path = await download_video(url=video_url, proxy=PROXY)
        segments.append(get_video_seg(video_path))

    # 下载图片
    for pic_url in pic_urls:
        img_path = await download_img(url=pic_url, proxy=PROXY)
        segments.append(get_img_seg(img_path))

    # 发送合并转发消息
    if segments:
        await send_segments(segments)


async def parse_x_url(x_url: str) -> tuple[list[str], list[str]]:
    """
    解析 X (Twitter) 链接获取视频和图片URL
    @author: biupiaa
    Returns:
        tuple[list[str], list[str]]: (视频URL列表, 图片URL列表)
    """

    async def x_req(url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://xdown.app",
            "Referer": "https://xdown.app/",
            **COMMON_HEADER,
        }
        data = {
            "q": url,
            "lang": "zh-cn"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post("https://xdown.app/api/ajaxSearch", headers=headers, data=data) as response:
                return await response.json()

    resp = await x_req(x_url)
    if resp.get("status") != "ok":
        raise ParseException("解析失败")

    html_content = resp.get("data", "")
    video_urls = []
    img_urls = []

    # 提取视频链接 (获取最高清晰度的视频)
    pattern = re.compile(
        r'<a\s+.*?href="(https?://dl\.snapcdn\.app/get\?token=.*?)"\s+rel="nofollow"\s+class="tw-button-dl button dl-success".*?>.*?下载 MP4 \((\d+p)\)</a>',
        re.DOTALL  # 允许.匹配换行符
    )
    video_pattern = pattern.findall(html_content)
    # 转换为带数值的元组以便排序
    processed = [
        (url, resolution, int(resolution.replace('p', '')))
        for url, resolution in video_pattern
    ]
    sorted_video_links = sorted(processed, key=lambda x: x[1], reverse=True)[0]
    if sorted_video_links:
        video_urls.append(sorted_video_links[0])

    # 提取图片链接
    img_urls = re.findall(r'<img src="(https://pbs\.twimg\.com/media/[^"]+)"', html_content)
    if not video_urls and not img_urls:
        raise ParseException("未找到可下载的媒体内容")

    return video_urls, img_urls
