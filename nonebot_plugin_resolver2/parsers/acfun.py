import json
import re
from typing import Any

import aiofiles
import aiohttp

from ..config import plugin_cache_dir
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
        tuple: 视频链接和视频名称
    """

    url_suffix = "?quickViewId=videoInfo_new&ajaxpipe=1"
    url = url + url_suffix
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=ACFUN_HEADERS) as resp:
            raw = await resp.text()
    strs_remove_header = raw.split("window.pageInfo = window.videoInfo =")
    strs_remove_tail = strs_remove_header[1].split("</script>")
    str_json = strs_remove_tail[0]
    str_json_escaped = escape_special_chars(str_json)
    video_info = json.loads(str_json_escaped)

    video_name = parse_video_name_fixed(video_info)
    ks_play_json = video_info["currentVideoInfo"]["ksPlayJson"]
    ks_play = json.loads(ks_play_json)
    representations = ks_play["adaptationSet"][0]["representation"]
    # 这里[d['url'] for d in representations]，从 4k ~ 360，此处默认720p
    m3u8_url = [d["url"] for d in representations][3]

    return m3u8_url, video_name


async def parse_m3u8(m3u8_url: str):
    """解析m3u8链接

    Args:
        m3u8_url (str): m3u8链接

    Returns:
        tuple: 视频链接和视频名称
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

    # aria2c下载的文件名，就是取url最后一段，去掉末尾 url 参数(?之后是url参数)
    ts_names = [str(d.split("?")[0]) for d in m3u8_relative_links]
    output_folder_name = ts_names[0][:-9]
    output_file_name = output_folder_name + ".mp4"
    return m3u8_full_urls, ts_names, output_file_name


async def download_m3u8_videos(m3u8_full_url: str, idx: int) -> None:
    """下载m3u8视频

    Args:
        m3u8_full_url (str): m3u8链接
        idx (int): 文件名
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(m3u8_full_url, headers=ACFUN_HEADERS) as resp:
            async with aiofiles.open(plugin_cache_dir / f"{idx}.ts", "wb") as f:
                async for chunk in resp.content.iter_chunked(1024):
                    await f.write(chunk)


def parse_video_name(video_info: dict[str, Any]) -> str:
    """获取视频信息

    Args:
        video_info (dict[str, Any]): 视频信息

    Returns:
        str: 视频信息
    """
    ac_id = "ac" + video_info.get("dougaId", "")
    title = video_info.get("title", "")
    author = video_info.get("user", {}).get("name", "")
    upload_time = video_info.get("createTime", "")
    desc = video_info.get("description", "")

    raw = "_".join([ac_id, title, author, upload_time, desc])[:101]
    return raw


async def merge_ac_file_to_mp4(ts_names: list[str], file_name: str) -> None:
    """合并ac文件到mp4

    Args:
        ts_names (list[str]): ts文件名
        file_name (str): 文件名
    """
    from ..download.utils import exec_ffmpeg_cmd

    concat_str = "\n".join([f"file {i}.ts" for i, d in enumerate(ts_names)])

    filetxt = plugin_cache_dir / "file.txt"
    filepath = plugin_cache_dir / file_name
    async with aiofiles.open(filetxt, "w") as f:
        await f.write(concat_str)
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(filetxt),  # Path 对象转字符串
        "-c",
        "copy",
        str(filepath),  # 自动处理路径空格
    ]

    await exec_ffmpeg_cmd(command)


def parse_video_name_fixed(video_info: dict) -> str:
    """校准文件名

    Args:
        video_info (dict): 视频信息

    Returns:
        str: 校准后的文件名
    """
    f = parse_video_name(video_info)
    t = f.replace(" ", "-")
    return t
