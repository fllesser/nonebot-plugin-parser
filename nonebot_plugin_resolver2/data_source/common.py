import json
import os
import re
import time
import aiofiles
import httpx

from typing import Set, Dict
from urllib.parse import urlparse
from pathlib import Path
from nonebot import logger

from ..constant import COMMON_HEADER
from ..config import store, plugin_cache_dir

async def download_video(url, proxy: str = None, ext_headers: Dict[str, str] = {}) -> Path:
    if not url:
        raise EmptyURLError("video url cannot be empty")
    video_name = parse_url_resource_name(url).split(".")[0] + ".mp4"
    video_path = plugin_cache_dir / video_name
    if video_path.exists():
        return video_path
    client_config = {
        'headers': COMMON_HEADER | ext_headers,
        'timeout': httpx.Timeout(60, connect=5.0),
        'follow_redirects': True
    }
    # 配置代理
    if proxy:
        client_config['proxies'] = { 'http://': proxy }

    # 下载文件
    async with httpx.AsyncClient(**client_config) as client:
        async with client.stream("GET", url) as resp:
            async with aiofiles.open(video_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    await f.write(chunk)
    return video_path


async def download_img(url: str, img_name: str = "", proxy: str = None, ext_headers = {}) -> Path:
    if not url:
        raise EmptyURLError("image url cannot be empty")
    img_name = img_name if img_name else parse_url_resource_name(url)
    img_path = plugin_cache_dir / img_name
    if img_path.exists():
        return img_path
    client_config = {
        'headers': COMMON_HEADER | ext_headers,
        'timeout': httpx.Timeout(60, connect=5.0),
        'follow_redirects': True
    }
    # 配置代理
    if proxy:
        client_config['proxies'] = { 'http://': proxy }

    # 下载文件
    async with httpx.AsyncClient(**client_config) as client:
        response = await client.get(url)
        response.raise_for_status()
    async with aiofiles.open(img_path, "wb") as f:
        await f.write(response.content)
    return img_path


async def download_audio(url: str) -> Path:
    if not url:
        raise EmptyURLError("audii url cannot be empty")
    
    # 从URL中提取文件名
    audio_name = parse_url_resource_name(url)
    audio_path = plugin_cache_dir / audio_name
    
    if audio_path.exists():
        return audio_path
        
    client_config = {
        'headers': COMMON_HEADER,
        'timeout': httpx.Timeout(60, connect=5.0),
        'follow_redirects': True
    }
    # download auido
    async with httpx.AsyncClient(**client_config) as client:
        async with client.stream("GET", url) as resp:
            async with aiofiles.open(audio_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    await f.write(chunk)
    return audio_path


def parse_url_resource_name(url: str) -> str:
    return urlparse(url).path.split('/')[-1]


def delete_boring_characters(sentence: str) -> str:
    """
        去除标题的特殊字符
    :param sentence:
    :return:
    """
    return re.sub(r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+', "", sentence)


class EmptyURLError(Exception):
    pass