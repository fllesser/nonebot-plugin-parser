import os
import re
import json
import time
import httpx
import hashlib
import asyncio
import aiofiles
import subprocess

from pathlib import Path
from nonebot.log import logger
from tqdm.asyncio import tqdm
from urllib.parse import urlparse

from ..constant import COMMON_HEADER
from ..config import plugin_cache_dir

class EmptyURLError(Exception):
    pass

def parse_url_resource_name(url: str) -> str:
    url_paths = urlparse(url).path.split('/')
    # 过滤掉空字符串并去除两端空白
    filtered_paths = [segment.strip() for segment in url_paths if segment.strip()]
    # 获取最后一个非空路径段
    last_path = filtered_paths[-1] if filtered_paths else ""
    pattern = r'[a-zA-Z0-9-]+(?:\.[a-zA-Z]+)?'

    if matches := re.findall(pattern, last_path):
        return ''.join(matches)
    else:
        return str(time.time())

def parse_url_file_name(url: str) -> str:
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    file_suffix = os.path.splitext(file_name)[1]
    return f'{hash16url(url)}{file_suffix}'

def hash16url(url: str) -> str:
    # 使用SHA-256哈希函数生成文件名
    hash_object = hashlib.sha256(url.encode())
    filename = hash_object.hexdigest()[-16:]
    return filename
    
async def download_file_by_stream(
    url: str,
    file_name: str = None,
    proxy: str = None,
    ext_headers: dict[str, str] = None
) -> Path:
    file_name = file_name if file_name is not None else parse_url_resource_name(url)
    file_path = plugin_cache_dir / file_name
    if file_path.exists():
        return file_path
    # httpx client config
    client_config =  {
        'timeout': httpx.Timeout(60, connect=5.0),
        'follow_redirects': True
    }
    if ext_headers is not None:
        client_config['headers'] = COMMON_HEADER | ext_headers
    if proxy is not None:
        client_config['proxies'] = { 
            'http://': proxy,
            'https://': proxy 
        }
        
    async with httpx.AsyncClient(**client_config) as client:
        async with client.stream("GET", url) as resp:
            if resp.status_code >= 400:
                resp.raise_for_status()
            with tqdm(
                total=int(resp.headers.get('content-length', 0)),
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                dynamic_ncols=True,
                colour='green'
            ) as bar:
                # 设置前缀信息
                bar.set_description(file_name)
                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        await f.write(chunk)
                        bar.update(len(chunk))
    return file_path
    
async def download_video(
    url: str,
    video_name: str = None,
    proxy: str = None,
    ext_headers: dict[str, str] = None
) -> Path:
    if video_name is not None:
        video_name = parse_url_resource_name(url).split(".")[0] + ".mp4"
    return await download_file_by_stream(url, video_name, proxy, ext_headers)

async def download_audio(
    url: str,
    audio_name: str = None,
    proxy: str = None,
    ext_headers: dict[str, str] = None
) -> Path:
    return await download_file_by_stream(url, audio_name, proxy, ext_headers)

async def download_img(
    url: str,
    img_name: str = None,
    proxy: str = None,
    ext_headers: dict[str, str] = None
) -> Path:
    return await download_file_by_stream(url, img_name, proxy, ext_headers)
    
async def merge_av(
    v_path: Path,
    a_path: Path,
    output_path: Path
):
    """
    合并视频文件和音频文件
    """
    logger.info(f'Merging {v_path.name} and {a_path.name} to {output_path.name}')
    # 构建 ffmpeg 命令, localstore already path.resolve()
    command = f'ffmpeg -y -i "{v_path}" -i "{a_path}" -c copy "{output_path}"'
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.call(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    )
    if result != 0:
        raise RuntimeError("ffmpeg未安装或命令执行失败")

def delete_boring_characters(sentence: str) -> str:
    """
        去除标题的特殊字符
    :param sentence:
    :return:
    """
    return re.sub(r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+', "", sentence)
