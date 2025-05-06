import asyncio
import re
from typing import Any

import aiohttp
from nonebot import logger, on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule

from ..config import NICKNAME, PROXY
from ..constant import COMMON_HEADER
from ..download import download_img, download_video
from ..exception import ParseException, handle_exception
from .filter import is_not_in_disabled_groups
from .helper import get_img_seg, get_video_seg, send_segments

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

    video_url, pic_urls = await parse_x_url(x_url)

    if video_url:
        video_path = await download_video(url=video_url, proxy=PROXY)
        await twitter.send(get_video_seg(video_path))

    if pic_urls:
        tasks = [download_img(url=pic_url, proxy=PROXY) for pic_url in pic_urls]
        img_paths = await asyncio.gather(*tasks)
        await send_segments([get_img_seg(img_path) for img_path in img_paths])


async def parse_x_url(x_url: str) -> tuple[str, list[str]]:
    """
    解析 X (Twitter) 链接获取视频和图片URL
    @author: biupiaa
    Returns:
        tuple[str, list[str]]: (视频 URL, 图片 URL 列表)
    """

    async def x_req(url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://xdown.app",
            "Referer": "https://xdown.app/",
            **COMMON_HEADER,
        }
        data = {"q": url, "lang": "zh-cn"}
        async with aiohttp.ClientSession() as session:
            async with session.post("https://xdown.app/api/ajaxSearch", headers=headers, data=data) as response:
                return await response.json()

    resp = await x_req(x_url)
    if resp.get("status") != "ok":
        raise ParseException("解析失败")

    html_content = resp.get("data", "")
    # 提取视频链接 (获取最高清晰度的视频)
    pattern = re.compile(
        r'<a\s+.*?href="(https?://dl\.snapcdn\.app/get\?token=.*?)"\s+rel="nofollow"\s+class="tw-button-dl button dl-success".*?>.*?下载 MP4 \((\d+p)\)</a>',  # noqa: E501
        re.DOTALL,  # 允许.匹配换行符
    )
    video_matches = pattern.findall(html_content)
    # 转换为带数值的元组以便排序
    if video_matches:
        best_video_url = max(
            ((str(url), int(resolution.replace("p", ""))) for url, resolution in video_matches), key=lambda x: x[1]
        )[0]
        # 最高质量视频
        return best_video_url, []

    # 提取图片链接
    img_urls = re.findall(r'<img src="(https://pbs\.twimg\.com/media/[^"]+)"', html_content)
    if img_urls:
        return "", img_urls
    raise ParseException("未找到可下载的媒体内容")
