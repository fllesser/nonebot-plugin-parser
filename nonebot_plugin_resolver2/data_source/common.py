import json
import os
import re
import time
import aiofiles
import httpx

from typing import Set, Dict
from urllib.parse import urlparse
from nonebot import logger

from ..constant import COMMON_HEADER
from ..config import store, plugin_cache_dir

async def download_video(url, proxy: str = None, ext_headers: Dict[str, str] = {}) -> str:
    """
    异步下载（httpx）视频，并支持通过代理下载。
    文件名将使用时间戳生成，以确保唯一性。
    如果提供了代理地址，则会通过该代理下载视频。

    :param ext_headers:
    :param url: 要下载的视频的URL。
    :param proxy: 可选，下载视频时使用的代理服务器的URL。
    :return: 视频名称
    """
    # 使用时间戳生成文件名，确保唯一性
    file_name = f"{int(time.time())}.mp4"

    headers = COMMON_HEADER | ext_headers

    client_config = {
        'headers': headers,
        'timeout': httpx.Timeout(60, connect=5.0),
        'follow_redirects': True
    }
    # 配置代理
    if proxy:
        client_config['proxies'] = { 'http://': proxy }

    # 下载文件
    try:
        async with httpx.AsyncClient(**client_config) as client:
            async with client.stream("GET", url) as resp:
                async with aiofiles.open(plugin_cache_dir / file_name, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        await f.write(chunk)
        return file_name
    except Exception as e:
        logger.warning(f"下载视频错误: {e}")
        return None


async def download_img(url: str, img_name: str = "", proxy: str = None, ext_headers = {}) -> str:
    if not url:
        return ""
    img_name = img_name if img_name else f"{url.split('/').pop()}"
    headers = COMMON_HEADER | ext_headers

    client_config = {
        'headers': headers,
        'timeout': httpx.Timeout(60, connect=5.0),
        'follow_redirects': True
    }
    # 配置代理
    if proxy:
        client_config['proxies'] = { 'http://': proxy }

    # 下载文件
    try:
        async with httpx.AsyncClient(**client_config) as client:
            response = await client.get(url)
            response.raise_for_status()
        async with aiofiles.open(plugin_cache_dir / img_name, "wb") as f:
            await f.write(response.content)
        return img_name
    except Exception as e:
        logger.warning(f'download_img err:{e}')
        return None



async def download_audio(url) -> str:
    # 从URL中提取文件名
    parsed_url = urlparse(url)
    file_name = parsed_url.path.split('/')[-1]
    # 去除可能存在的请求参数
    file_name = file_name.split('?')[0]

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()  # 检查请求是否成功
    async with aiofiles.open(plugin_cache_dir / file_name, 'wb') as file:
        await file.write(response.content)
    return file_name


def delete_boring_characters(sentence: str) -> str:
    """
        去除标题的特殊字符
    :param sentence:
    :return:
    """
    return re.sub(r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+', "", sentence)
