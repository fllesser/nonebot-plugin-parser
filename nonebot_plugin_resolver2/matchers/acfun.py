import asyncio
import json
import re

import aiofiles
import aiohttp
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.log import logger
from nonebot.rule import Rule

from nonebot_plugin_resolver2.config import NICKNAME, plugin_cache_dir

from .filter import is_not_in_disabled_groups
from .utils import get_video_seg

acfun = on_keyword(keywords={"acfun.cn"}, rule=Rule(is_not_in_disabled_groups))


@acfun.handle()
async def _(event: MessageEvent) -> None:
    message: str = event.message.extract_plain_text().strip()
    match = re.search(r"(?:ac=|/ac)(\d+)", message)
    if not match:
        logger.info("acfun url is incomplete, ignored")
        return
    url = f"https://www.acfun.cn/v/ac{match.group(1)}"
    url_m3u8s, video_name = await parse_url(url)
    await acfun.send(Message(f"{NICKNAME}解析 | 猴山 - {video_name}"))
    m3u8_full_urls, ts_names, output_file_name = await parse_m3u8(url_m3u8s)
    # logger.info(output_folder_name, output_file_name)
    await asyncio.gather(*[download_m3u8_videos(url, i) for i, url in enumerate(m3u8_full_urls)])
    await merge_ac_file_to_mp4(ts_names, output_file_name)
    await acfun.send(await get_video_seg(plugin_cache_dir / output_file_name))


headers = {
    "referer": "https://www.acfun.cn/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83",  # noqa: E501
}


async def parse_url(url: str):
    """
    解析acfun链接
    :param url:
    :return:
    """
    url_suffix = "?quickViewId=videoInfo_new&ajaxpipe=1"
    url = url + url_suffix
    # print(url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            raw = await resp.text()
    strs_remove_header = raw.split("window.pageInfo = window.videoInfo =")
    strs_remove_tail = strs_remove_header[1].split("</script>")
    str_json = strs_remove_tail[0]
    str_json_escaped = escape_special_chars(str_json)
    video_info = json.loads(str_json_escaped)
    # print(video_info)
    video_name = parse_video_name_fixed(video_info)
    ks_play_json = video_info["currentVideoInfo"]["ksPlayJson"]
    ks_play = json.loads(ks_play_json)
    representations = ks_play["adaptationSet"][0]["representation"]
    # 这里[d['url'] for d in representations]，从4k~360，此处默认720p
    url_m3u8s = [d["url"] for d in representations][3]
    # print([d['url'] for d in representations])
    return url_m3u8s, video_name


async def parse_m3u8(m3u8_url: str):
    """
        解析m3u8链接
    :param m3u8_url:
    :return:
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(m3u8_url, headers=headers) as resp:
            m3u8_file = await resp.text()
    # 分离ts文件链接
    raw_pieces = re.split(r"\n#EXTINF:.{8},\n", m3u8_file)
    # print(raw_pieces)
    # 过滤头部\
    m3u8_relative_links = raw_pieces[1:]
    # print(m3u8_relative_links)
    # 修改尾部 去掉尾部多余的结束符
    patched_tail = m3u8_relative_links[-1].split("\n")[0]
    m3u8_relative_links[-1] = patched_tail
    # print(m3u8_relative_links)

    # 完整链接，直接加m3u8Url的通用前缀
    m3u8_prefix = "/".join(m3u8_url.split("/")[0:-1])
    m3u8_full_urls = [m3u8_prefix + "/" + d for d in m3u8_relative_links]
    # aria2c下载的文件名，就是取url最后一段，去掉末尾url参数(?之后是url参数)
    ts_names = [d.split("?")[0] for d in m3u8_relative_links]
    output_folder_name = ts_names[0][:-9]
    output_file_name = output_folder_name + ".mp4"
    return m3u8_full_urls, ts_names, output_file_name


async def download_m3u8_videos(m3u8_full_url, i):
    """
    批量下载m3u8
    :param m3u8_full_urls:
    :return:
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(m3u8_full_url, headers=headers) as resp:
            async with aiofiles.open(plugin_cache_dir / f"{i}.ts", "wb") as f:
                async for chunk in resp.content.iter_chunked(1024):
                    await f.write(chunk)


def escape_special_chars(str_json):
    return str_json.replace('\\\\"', '\\"').replace('\\"', '"')


def parse_video_name(video_info: dict):
    """
    获取视频信息
    :param video_info:
    :return:
    """
    ac_id = "ac" + video_info["dougaId"] if video_info["dougaId"] is not None else ""
    title = video_info["title"] if video_info["title"] is not None else ""
    author = video_info["user"]["name"] if video_info["user"]["name"] is not None else ""
    upload_time = video_info["createTime"] if video_info["createTime"] is not None else ""
    desc = video_info["description"] if video_info["description"] is not None else ""

    raw = "_".join([ac_id, title, author, upload_time, desc])[:101]
    return raw


async def merge_ac_file_to_mp4(ts_names, file_name):
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

    try:
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # 等待进程完成并捕获输出
        _, stderr = await process.communicate()
        return_code = process.returncode

    except FileNotFoundError:
        raise RuntimeError("ffmpeg 未安装或无法找到可执行文件")

    if return_code != 0:
        error_msg = stderr.decode().strip()
        raise RuntimeError(f"ffmpeg 执行失败: {error_msg}")


def parse_video_name_fixed(video_info: dict):
    """
    校准文件名
    :param video_info:
    :return:
    """
    f = parse_video_name(video_info)
    t = f.replace(" ", "-")
    return t
