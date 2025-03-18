import asyncio
from pathlib import Path

import aiofiles
import aiohttp
from nonebot.log import logger
from tqdm.asyncio import tqdm

from nonebot_plugin_resolver2.config import plugin_cache_dir
from nonebot_plugin_resolver2.constant import COMMON_HEADER

from .utils import exec_ffmpeg_cmd, generate_file_name, safe_unlink

# 创建一个全局 session 对象
_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    """获取或创建全局 session 对象"""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300, connect=10.0))
    return _session


async def download_file_by_stream(
    url: str,
    *,
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
        file_name = generate_file_name(url)
    file_path = plugin_cache_dir / file_name
    if file_path.exists():
        return file_path

    headers = COMMON_HEADER.copy()
    if ext_headers is not None:
        headers.update(ext_headers)

    session = await _get_session()
    try:
        async with session.get(url, headers=headers, proxy=proxy) as resp, aiofiles.open(file_path, "wb") as file:
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
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    await file.write(chunk)
                    bar.update(len(chunk))
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"url: {url}, file_path: {file_path} 下载过程中出现异常{e}")
        raise

    return file_path


async def download_video(
    url: str,
    *,
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
        video_name = generate_file_name(url, ".mp4")
    return await download_file_by_stream(url, file_name=video_name, proxy=proxy, ext_headers=ext_headers)


async def download_audio(
    url: str,
    *,
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
        audio_name = generate_file_name(url, ".mp3")
    return await download_file_by_stream(url, file_name=audio_name, proxy=proxy, ext_headers=ext_headers)


async def download_img(
    url: str,
    *,
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
        img_name = generate_file_name(url, ".jpg")
    return await download_file_by_stream(url, file_name=img_name, proxy=proxy, ext_headers=ext_headers)


async def download_imgs_without_raise(urls: list[str], ext_headers: dict[str, str] | None = None) -> list[Path]:
    """download images without raise

    Args:
        urls (list[str]): urls
        ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

    Returns:
        list[Path]: image file paths
    """
    paths_or_errs = await asyncio.gather(
        *[download_img(url, ext_headers=ext_headers) for url in urls], return_exceptions=True
    )
    return [p for p in paths_or_errs if isinstance(p, Path)]


async def merge_av(*, v_path: Path, a_path: Path, output_path: Path) -> None:
    logger.info(f"Merging {v_path.name} and {a_path.name} to {output_path.name}")

    # 显式指定流映射
    cmd = [
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

    await exec_ffmpeg_cmd(cmd)
    await asyncio.gather(safe_unlink(v_path), safe_unlink(a_path))


async def merge_av_h264(*, v_path: Path, a_path: Path, output_path: Path) -> None:
    logger.info(f"Merging {v_path.name} and {a_path.name} to {output_path.name}")

    # 修改命令以确保视频使用 H.264 编码
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(v_path),
        "-i",
        str(a_path),
        "-c:v",
        "libx264",  # 明确指定使用 H.264 编码
        "-preset",
        "medium",  # 编码速度和质量的平衡
        "-crf",
        "23",  # 质量因子，值越低质量越高
        "-c:a",
        "aac",  # 音频使用 AAC 编码
        "-b:a",
        "128k",  # 音频比特率
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        str(output_path),
    ]

    await exec_ffmpeg_cmd(cmd)
    await asyncio.gather(safe_unlink(v_path), safe_unlink(a_path))


# 将视频重新编码到 h264
async def re_encode_video(video_path: Path) -> Path:
    output_path = video_path.with_name(f"{video_path.stem}_h264{video_path.suffix}")
    if output_path.exists():
        return output_path
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        str(output_path),
    ]
    await exec_ffmpeg_cmd(cmd)
    logger.success(f"视频重新编码为 H.264 成功: {output_path}, 大小: {output_path.stat().st_size / 1024 / 1024:.2f}MB")
    await asyncio.gather(safe_unlink(video_path))
    return output_path
