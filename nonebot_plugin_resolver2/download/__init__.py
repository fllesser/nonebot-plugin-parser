import asyncio
from pathlib import Path

import aiofiles
import aiohttp
from nonebot.log import logger
from tqdm.asyncio import tqdm

from ..config import MAX_SIZE, plugin_cache_dir
from ..constant import COMMON_HEADER
from ..exception import DownloadException
from .utils import exec_ffmpeg_cmd, generate_file_name, safe_unlink

# 全局 session
_SESSION: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    """获取或创建全局 session"""
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300, connect=10.0))
    return _SESSION


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

    Raises:
        aiohttp.ClientError: When download fails
        asyncio.TimeoutError: When download times out
    """
    if not file_name:
        file_name = generate_file_name(url)
    file_path = plugin_cache_dir / file_name

    # 如果文件存在，则直接返回
    if file_path.exists():
        return file_path

    headers = {**COMMON_HEADER, **(ext_headers or {})}

    try:
        session = await _get_session()
        async with session.get(url, headers=headers, proxy=proxy) as resp:
            resp.raise_for_status()
            # 获取文件大小
            content_length = resp.headers.get("Content-Length")
            content_length = int(content_length) if content_length else None
            if content_length and (file_size := content_length / 1024 / 1024) > MAX_SIZE:
                logger.warning(f"预下载文件 {file_name} 大小 {file_size:.2f} MB 超过 {MAX_SIZE} MB 限制, 取消下载")
                raise DownloadException("音视频流大小超过限制，取消下载")
            with tqdm(
                total=content_length,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                dynamic_ncols=True,
                colour="green",
                desc=file_name,
            ) as bar:
                async with aiofiles.open(file_path, "wb") as file:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        await file.write(chunk)
                        bar.update(len(chunk))
    except asyncio.TimeoutError:
        await safe_unlink(file_path)
        logger.error(f"url: {url}, file_path: {file_path} 下载超时")
        raise DownloadException("资源下载超时")
    except aiohttp.ClientError as e:
        await safe_unlink(file_path)
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

    Raises:
        aiohttp.ClientError: When download fails
        asyncio.TimeoutError: When download times out
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

    Raises:
        aiohttp.ClientError: When download fails
        asyncio.TimeoutError: When download times out
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

    Raises:
        aiohttp.ClientError: When download fails
        asyncio.TimeoutError: When download times out
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
    """合并视频和音频

    Args:
        v_path (Path): 视频文件路径
        a_path (Path): 音频文件路径
        output_path (Path): 输出文件路径
    """
    logger.info(f"Merging {v_path.name} and {a_path.name} to {output_path.name}")

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
    """合并视频和音频，并使用 H.264 编码

    Args:
        v_path (Path): 视频文件路径
        a_path (Path): 音频文件路径
        output_path (Path): 输出文件路径
    """
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


async def encode_video_to_h264(video_path: Path) -> Path:
    """将视频重新编码到 h264

    Args:
        video_path (Path): 视频路径

    Returns:
        Path: 编码后的视频路径
    """
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
    await safe_unlink(video_path)
    return output_path
