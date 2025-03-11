import asyncio
from collections import deque
from pathlib import Path
import re
import time

import aiofiles
import aiohttp
from nonebot.log import logger
from tqdm.asyncio import tqdm

from nonebot_plugin_resolver2.config import plugin_cache_dir
from nonebot_plugin_resolver2.constant import COMMON_HEADER


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

    headers = COMMON_HEADER.copy()
    if ext_headers is not None:
        headers.update(ext_headers)

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=300, connect=10.0)) as resp:
                resp.raise_for_status()
                with tqdm(
                    total=int(resp.headers.get("Content-Length", 0)),
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    dynamic_ncols=True,
                    colour="green",
                ) as bar:
                    # 设置前缀信息
                    bar.set_description(file_name)
                    async with aiofiles.open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024):
                            await f.write(chunk)
                            bar.update(len(chunk))
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"url: {url}, file_path: {file_path} 下载过程中出现异常{e}")
            raise

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


async def download_imgs_without_raise(urls: list[str]) -> list[Path]:
    """download images without raise

    Args:
        urls (list[str]): urls

    Returns:
        list[Path]: image file paths
    """
    paths_or_errs = await asyncio.gather(*[download_img(url) for url in urls], return_exceptions=True)
    return [p for p in paths_or_errs if isinstance(p, Path)]


async def merge_av(v_path: Path, a_path: Path, output_path: Path) -> None:
    logger.info(f"Merging {v_path.name} and {a_path.name} to {output_path.name}")

    # 显式指定流映射
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(v_path),
        "-i",
        str(a_path),
        "-c",
        "copy",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        str(output_path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        return_code = process.returncode
    except FileNotFoundError:
        raise RuntimeError("ffmpeg 未安装或无法找到可执行文件")

    if return_code != 0:
        error_msg = stderr.decode().strip()
        raise RuntimeError(f"ffmpeg 执行失败: {error_msg}")

    # 安全删除文件
    async def safe_unlink(path: Path):
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except Exception as e:
            logger.error(f"删除 {path} 失败: {e}")

    await asyncio.gather(safe_unlink(v_path), safe_unlink(a_path))


# A deque to store the URL to file name mapping
url_file_mapping: deque[tuple[str, str]] = deque(maxlen=20)


def generate_file_name(url: str, type: str) -> str:
    if file_name := next(
        (f for u, f in url_file_mapping if u == url),
        None,
    ):
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
    url_file_mapping.append((url, file_name))
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
