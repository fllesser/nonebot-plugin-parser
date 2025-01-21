import re
import time
import httpx
import asyncio
import aiofiles
import subprocess

from pathlib import Path
from nonebot.log import logger
from tqdm.asyncio import tqdm

from ..constant import COMMON_HEADER
from ..config import plugin_cache_dir

async def download_file_by_stream(
    url: str,
    file_name: str | None = None,
    proxy: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download file by url with stream

    Args:
        url (str): url address
        file_name (str | None, optional): file name. Defaults to get name by parse_url_resource_name.
        proxy (str | None, optional): proxy url. Defaults to None.
        ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

    Returns:
        Path: file path
    """
    # file_name = file_name if file_name is not None else parse_url_resource_name(url)
    if not file_name:
        file_name = generate_file_name(url, "file")
    file_path = plugin_cache_dir / file_name
    if file_path.exists():
        return file_path
    # httpx client config
    client_config = {
        "timeout": httpx.Timeout(60, connect=5.0),
        "follow_redirects": True,
    }
    if ext_headers is not None:
        client_config["headers"] = COMMON_HEADER | ext_headers
    if proxy is not None:
        client_config["proxies"] = {"http://": proxy, "https://": proxy}

    async with httpx.AsyncClient(**client_config) as client:
        async with client.stream("GET", url) as resp:
            if resp.status_code >= 400:
                resp.raise_for_status()
            with tqdm(
                total=int(resp.headers.get("content-length", 0)),
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                dynamic_ncols=True,
                colour="green",
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
    video_name: str | None = None,
    proxy: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download video file by url with stream

    Args:
        url (str): url address
        video_name (str | None, optional): video name. Defaults to get name by parse url.
        proxy (str | None, optional): proxy url. Defaults to None.
        ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

    Returns:
        Path: video file path
    """
    if video_name is None:
        video_name = generate_file_name(url, "video")
    return await download_file_by_stream(url, video_name, proxy, ext_headers)

async def download_audio(
    url: str,
    audio_name: str | None = None,
    proxy: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download audio file by url with stream

    Args:
        url (str): url address
        audio_name (str | None, optional): audio name. Defaults to get name by parse_url_resource_name.
        proxy (str | None, optional): proxy url. Defaults to None.
        ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

    Returns:
        Path: audio file path
    """
    if audio_name is None:
        audio_name = generate_file_name(url, "audio")
    return await download_file_by_stream(url, audio_name, proxy, ext_headers)


async def download_img(
    url: str,
    img_name: str | None = None,
    proxy: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download image file by url with stream

    Args:
        url (str): url
        img_name (str, optional): image name. Defaults to None.
        proxy (str, optional): proxry url. Defaults to None.
        ext_headers (dict[str, str], optional): ext headers. Defaults to None.

    Returns:
        Path: image file path
    """
    if img_name is None:
        img_name = generate_file_name(url, "image")
    return await download_file_by_stream(url, img_name, proxy, ext_headers)


async def merge_av(v_path: Path, a_path: Path, output_path: Path):
    """helper function to merge video and audio

    Args:
        v_path (Path): video path
        a_path (Path): audio path
        output_path (Path): ouput path

    Raises:
        RuntimeError: ffmpeg未安装或命令执行失败
    """
    logger.info(f"Merging {v_path.name} and {a_path.name} to {output_path.name}")
    # 构建 ffmpeg 命令, localstore already path.resolve()
    command = f'ffmpeg -y -i "{v_path}" -i "{a_path}" -c copy "{output_path}"'
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.call(
            command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ),
    )
    if result != 0:
        raise RuntimeError("ffmpeg未安装或命令执行失败")

url_file_mapping: dict[str, str] = {}

def generate_file_name(url: str, type: str) -> str:
    global url_file_mapping
    if file_name := url_file_mapping.get(url):
        return file_name
    suffix = ""
    match type:
        case "audio":
            suffix = ".mp3"
        case "image":
            suffix = ".jpg"
        case "video":
            suffix = ".mp4"
        case _: 
            if match := re.search(r"(\.[a-zA-Z0-9]+)\?", url):
                suffix = match.group(1) if match else ""
    file_name = f"{type}_{int(time.time())}_{hash(url)}{suffix}"
    url_file_mapping[url] = file_name
    return file_name

def delete_boring_characters(sentence: str) -> str:
    """
    去除标题的特殊字符
    :param sentence:
    :return:
    """
    return re.sub(
        r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+',
        "",
        sentence,
    )
