import asyncio
import json
from pathlib import Path
import re
from typing_extensions import deprecated

import aiofiles
import aiohttp

from ..config import MAX_SIZE, plugin_cache_dir
from ..download import download_file_by_stream
from ..download.utils import safe_unlink
from ..exception import DownloadException
from .utils import escape_special_chars

ACFUN_HEADERS = {
    "referer": "https://www.acfun.cn/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83",  # noqa: E501
}


async def parse_acfun_url(url: str) -> tuple[str, str]:
    """解析acfun链接

    Args:
        url (str): 链接

    Returns:
        tuple: 视频链接和视频描述
    """
    # 拼接查询参数
    url = f"{url}?quickViewId=videoInfo_new&ajaxpipe=1"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=ACFUN_HEADERS) as resp:
            resp.raise_for_status()
            raw = await resp.text()

    # 分离视频信息和 ksPlayJson
    strs_remove_header = raw.split("window.pageInfo = window.videoInfo =")
    strs_remove_tail = strs_remove_header[1].split("</script>")
    str_json = strs_remove_tail[0]
    str_json_escaped = escape_special_chars(str_json)
    video_info = json.loads(str_json_escaped)

    video_desc = (
        f"ac{video_info.get('dougaId', '')}\n"
        f"标题: {video_info.get('title', '')}\n"
        f"简介: {video_info.get('description', '')}\n"
        f"作者: {video_info.get('user', {}).get('name', '')}, 上传于 {video_info.get('createTime', '')}"
    )

    ks_play_json = video_info["currentVideoInfo"]["ksPlayJson"]
    ks_play = json.loads(ks_play_json)
    representations = ks_play["adaptationSet"][0]["representation"]
    # 这里[d['url'] for d in representations]，从 4k ~ 360，此处默认720p
    m3u8_url = [d["url"] for d in representations][3]

    return m3u8_url, video_desc


async def download_acfun_video(m3u8s_url: str, acid: int) -> Path:
    """下载acfun视频

    Args:
        m3u8s_url (str): m3u8链接
        acid (int): acid

    Returns:
        Path: 下载的mp4文件
    """
    from tqdm.asyncio import tqdm

    m3u8_full_urls = await _parse_m3u8(m3u8s_url)
    video_file = plugin_cache_dir / f"acfun_{acid}.mp4"
    if video_file.exists():
        return video_file

    try:
        max_size_in_bytes = MAX_SIZE * 1024 * 1024
        async with aiofiles.open(video_file, "wb") as f, aiohttp.ClientSession() as session:
            total_size = 0
            with tqdm(
                total=None,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                dynamic_ncols=True,
                colour="green",
                desc=video_file.name,
            ) as bar:
                for url in m3u8_full_urls:
                    async with session.get(url, headers=ACFUN_HEADERS) as resp:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
                            total_size += len(chunk)
                            bar.update(len(chunk))
                    if total_size > max_size_in_bytes:
                        # 直接截断
                        break
    except aiohttp.ClientError as e:
        await safe_unlink(video_file)
        raise DownloadException(f"下载 acfun 视频失败: {e}")
    except asyncio.TimeoutError:
        await safe_unlink(video_file)
        raise DownloadException("下载 acfun 视频超时")
    return video_file


async def _parse_m3u8(m3u8_url: str):
    """解析m3u8链接

    Args:
        m3u8_url (str): m3u8链接

    Returns:
        list[str]: 视频链接
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(m3u8_url, headers=ACFUN_HEADERS) as resp:
            m3u8_file = await resp.text()
    # 分离ts文件链接
    raw_pieces = re.split(r"\n#EXTINF:.{8},\n", m3u8_file)
    # 过滤头部\
    m3u8_relative_links = raw_pieces[1:]

    # 修改尾部 去掉尾部多余的结束符
    patched_tail = m3u8_relative_links[-1].split("\n")[0]
    m3u8_relative_links[-1] = patched_tail

    # 完整链接，直接加 m3u8Url 的通用前缀
    m3u8_prefix = "/".join(m3u8_url.split("/")[0:-1])
    m3u8_full_urls = [f"{m3u8_prefix}/{d}" for d in m3u8_relative_links]

    return m3u8_full_urls


@deprecated("已废弃，请使用 download_acfun_video 代替")
async def _merge_acs_to_mp4(acid: int, ts_files: list[Path]) -> Path:
    """合并ac文件到mp4

    Args:
        acid (int): acid
        ts_files (list[Path]): ts文件

    Returns:
        Path: 合并后的mp4文件
    """
    from ..download.utils import exec_ffmpeg_cmd

    concat_str = "\n".join([f"file {d.name}" for d in ts_files])

    txt_file = plugin_cache_dir / f"acfun_{acid}.txt"
    video_file = plugin_cache_dir / f"acfun_{acid}.mp4"
    async with aiofiles.open(txt_file, "w") as f:
        await f.write(concat_str)
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(txt_file),
        "-c",
        "copy",
        str(video_file),
    ]

    await exec_ffmpeg_cmd(command)
    return video_file


@deprecated("已废弃，请使用 download_acfun_video 代替")
async def download_and_merge_acfun_video(m3u8s_url: str, acid: int) -> Path:
    """下载并合并acfun视频

    Args:
        m3u8s_url (str): m3u8链接
        acid (int): acid

    Returns:
        Path: 合并后的mp4文件
    """
    m3u8_full_urls = await _parse_m3u8(m3u8s_url)
    ts_paths = await asyncio.gather(*[download_file_by_stream(url) for url in m3u8_full_urls])
    return await _merge_acs_to_mp4(acid, ts_paths)
