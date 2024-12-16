from typing import Iterable, List
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..constant import VIDEO_MAX_MB
from ..data_source.common import download_video, get_file_size_mb
from ..config import *


def make_node_segment(user_id, segments: MessageSegment | List[MessageSegment | str]) -> Iterable[MessageSegment]:
    """
        将消息封装成 Segment 的 Node 类型，可以传入单个也可以传入多个，返回一个封装好的转发类型
    :param user_id: 可以通过event获取
    :param segments: 一般为 MessageSegment.image / MessageSegment.video / MessageSegment.text
    :return:
    """
    return [(MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME, content=Message(segment))) 
            for segment in (segments if isinstance(segments, list) else [segments])]


async def get_video_seg(file_name: str = "", url: str = "") -> MessageSegment:
    seg: MessageSegment = None
    try:
        # 如果data以"http"开头，先下载视频
        if not file_name:
            if url and url.startswith("http"):
                file_name = await download_video(url)
        if not file_name:
            return MessageSegment.text(f"获取 video 出错, file_name: {file_name}, url: {url}")
        data_path = plugin_cache_dir / file_name
        # 检测文件大小
        file_size_bytes = int(data_path.stat().st_size)
        # file_size_in_mb = get_file_size_mb(data_path)
        # 如果视频大于 100 MB 自动转换为群文件, 先忽略
        if file_size_bytes == 0:
            seg = MessageSegment.text("获取视频失败")
        elif file_size_bytes > VIDEO_MAX_MB * 1024 * 1024:
            # 转为文件 Seg
            seg = get_file_seg(file_name)
        else:
            seg = MessageSegment.video(data_path)
    except Exception as e:
        # logger.error(f"转换为 segment 失败\n{e}")
        seg = MessageSegment.text(f"转换为 segment 失败\n{e}")
    finally:
        return seg
    
def get_file_seg(file_name: str, name: str = "") -> MessageSegment:
    file = plugin_cache_dir / file_name
    return MessageSegment("file", data = {
        "name": name if name else file_name,
        "file": file.resolve().as_uri()
    })
