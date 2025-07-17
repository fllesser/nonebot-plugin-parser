import asyncio
from pathlib import Path

import aiofiles
import httpx
from nonebot import logger
from tqdm.asyncio import tqdm

from ..config import MAX_SIZE, plugin_cache_dir
from ..constant import COMMON_HEADER, DOWNLOAD_TIMEOUT
from ..exception import DownloadException
from .utils import exec_ffmpeg_cmd, generate_file_name, safe_unlink


async def download_file_by_stream(
    url: str,
    *,
    file_name: str | None = None,
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
        httpx.HTTPError: When download fails
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
        async with httpx.AsyncClient(headers=headers, timeout=DOWNLOAD_TIMEOUT, verify=False) as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                content_length = int(content_length) if content_length else None
                if content_length and (file_size := content_length / 1024 / 1024) > MAX_SIZE:
                    logger.warning(f"预下载 {file_name} 大小 {file_size:.2f} MB 超过 {MAX_SIZE} MB 限制, 取消下载")
                    raise DownloadException("媒体大小超过配置限制，取消下载")
                with get_progress_bar(file_name, content_length) as bar:
                    async with aiofiles.open(file_path, "wb") as file:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            await file.write(chunk)
                            bar.update(len(chunk))
    except httpx.HTTPError as exc:
        await safe_unlink(file_path)
        logger.error(f"下载失败: url: {url}, file_path: {file_path} exc: {exc}")
        raise DownloadException(f"媒体下载失败: {exc}")
    return file_path


def get_progress_bar(desc: str, total: int | None = None) -> tqdm:
    return tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        dynamic_ncols=True,
        colour="green",
        desc=desc,
    )


async def download_video(
    url: str,
    *,
    video_name: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download video file by url with stream

    Args:
        url (str): url address
        video_name (str | None, optional): video name. Defaults to get name by parse url.
        ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

    Returns:
        Path: video file path

    Raises:
        httpx.HTTPError: When download fails
        asyncio.TimeoutError: When download times out
    """
    if video_name is None:
        video_name = generate_file_name(url, ".mp4")
    return await download_file_by_stream(url, file_name=video_name, ext_headers=ext_headers)


async def download_audio(
    url: str,
    *,
    audio_name: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download audio file by url with stream

    Args:
        url (str): url address
        audio_name (str | None, optional): audio name. Defaults to get name by parse_url_resource_name.
        ext_headers (dict[str, str] | None, optional): ext headers. Defaults to None.

    Returns:
        Path: audio file path

    Raises:
        httpx.HTTPError: When download fails
        asyncio.TimeoutError: When download times out
    """
    if audio_name is None:
        audio_name = generate_file_name(url, ".mp3")
    return await download_file_by_stream(url, file_name=audio_name, ext_headers=ext_headers)


async def download_img(
    url: str,
    *,
    img_name: str | None = None,
    ext_headers: dict[str, str] | None = None,
) -> Path:
    """download image file by url with stream

    Args:
        url (str): url
        img_name (str, optional): image name. Defaults to None.
        ext_headers (dict[str, str], optional): ext headers. Defaults to None.

    Returns:
        Path: image file path

    Raises:
        httpx.HTTPError: When download fails
        asyncio.TimeoutError: When download times out
    """
    if img_name is None:
        img_name = generate_file_name(url, ".jpg")
    return await download_file_by_stream(url, file_name=img_name, ext_headers=ext_headers)


async def download_imgs_without_raise(
    urls: list[str],
    *,
    ext_headers: dict[str, str] | None = None,
) -> list[Path]:
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
    logger.success(f"视频重新编码为 H.264 成功: {output_path}, {fmt_size(output_path)}")
    await safe_unlink(video_path)
    return output_path


def fmt_size(file_path: Path) -> str:
    """获取视频大小

    Args:
        video_path (Path): 视频路径
    """
    return f"大小: {file_path.stat().st_size / 1024 / 1024:.2f} MB"
