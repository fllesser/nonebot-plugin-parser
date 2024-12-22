import os
import re
import json
import time
import httpx
import asyncio
import aiofiles
import subprocess

from pathlib import Path
from nonebot.log import logger
from tqdm.asyncio import tqdm
from urllib.parse import urlparse

from ..constant import COMMON_HEADER
from ..config import store, plugin_cache_dir


client_base_config = {
    'headers': COMMON_HEADER,
    'timeout': httpx.Timeout(60, connect=5.0),
    'follow_redirects': True
}

async def download_video(
    url: str,
    proxy: str = None,
    ext_headers: dict[str, str] = None
) -> Path:
    if not url:
        raise EmptyURLError("video url cannot be empty")
    video_name = parse_url_resource_name(url).split(".")[0] + ".mp4"
    video_path = plugin_cache_dir / video_name
    if not video_path.exists():
        await download_file_by_stream(url, video_path, proxy, ext_headers)
    return video_path

async def download_img(
    url: str,
    img_name: str = "",
    proxy: str = None,
    ext_headers = None
) -> Path:
    if not url:
        raise EmptyURLError("image url cannot be empty")
    img_name = img_name if img_name else parse_url_resource_name(url)
    img_path = plugin_cache_dir / img_name
    if img_path.exists():
        return img_path
    # client config
    client_config = client_base_config.copy()
    if ext_headers:
        client_config['headers'].update(ext_headers)
    if proxy:
        client_config['proxies'] = { 
            'http://': proxy,
            'https://': proxy 
        }
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
    audio_path = plugin_cache_dir / parse_url_resource_name(url)
    if not audio_path.exists():
        await download_file_by_stream(url, audio_path)
    return audio_path

async def download_file_by_stream(
    url: str,
    file_path: Path, 
    proxy: str = None, 
    ext_headers: dict[str, str] = None
):
    client_config = client_base_config.copy()
    if ext_headers:
        client_config['headers'].update(ext_headers)
    # 配置代理
    if proxy:
        client_config['proxies'] = { 
            'http://': proxy,
            'https://': proxy 
        }
    # download
    async with httpx.AsyncClient(**client_config) as client:
        async with client.stream("GET", url) as resp:
            with tqdm(
                total=int(resp.headers.get('content-length', 0)),
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                dynamic_ncols=True,
                colour='green'
            ) as bar:
                # 设置前缀信息
                bar.set_description(file_path.name)
                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        await f.write(chunk)
                        bar.update(len(chunk))

async def merge_av(
    v_path: Path,
    a_path: Path,
    output_path: Path,
    log_output: bool = False
):
    """
    合并视频文件和音频文件
    """
    logger.info(f'正在合并: {output_path.name}')
    # 构建 ffmpeg 命令, localstore already path.resolve()
    command = f'ffmpeg -y -i {v_path.resolve()} -i "{a_path.resolve()}" -c copy "{output_path.resolve()}"'
    stdout = None if log_output else subprocess.DEVNULL
    stderr = None if log_output else subprocess.DEVNULL
    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.call(command, shell=True, stdout=stdout, stderr=stderr)
    )


def parse_url_resource_name(url: str) -> str:
    url_paths = urlparse(url).path.split('/')
    # 过滤掉空字符串并去除两端空白
    filtered_paths = [segment.strip() for segment in url_paths if segment.strip()]
    # 获取最后一个非空路径段
    return filtered_paths[-1] if filtered_paths else str(time.time())

def delete_boring_characters(sentence: str) -> str:
    """
        去除标题的特殊字符
    :param sentence:
    :return:
    """
    return re.sub(r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+', "", sentence)

class EmptyURLError(Exception):
    pass