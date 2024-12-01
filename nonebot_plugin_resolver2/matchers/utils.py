from typing import cast, Iterable, Union, List
from nonebot import logger

from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment, GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent, MessageEvent
from nonebot.matcher import current_bot

from ..constant import VIDEO_MAX_MB
from ..core.common import download_video, get_file_size_mb
from ..config import *

def auto_determine_send_type(user_id: int, task: str) -> MessageSegment:
    """
        判断是视频还是图片然后发送最后删除，函数在 twitter 这类可以图、视频混合发送的媒体十分有用
    :param user_id:
    :param task:
    :return:
    """
    if task.endswith("jpg") or task.endswith("png"):
        return MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME,
                                          content=Message(MessageSegment.image(task)))
    elif task.endswith("mp4"):
        return MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME,
                                          content=Message(MessageSegment.video(task)))


def make_node_segment(user_id, segments: Union[MessageSegment, List]) -> Union[
    MessageSegment, Iterable[MessageSegment]]:
    """
        将消息封装成 Segment 的 Node 类型，可以传入单个也可以传入多个，返回一个封装好的转发类型
    :param user_id: 可以通过event获取
    :param segments: 一般为 MessageSegment.image / MessageSegment.video / MessageSegment.text
    :return:
    """
    if isinstance(segments, list):
        return [MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME,
                                           content=Message(segment)) for segment in segments]
    return MessageSegment.node_custom(user_id=user_id, nickname=NICKNAME,
                                      content=Message(segments))


async def send_forward_both(bot: Bot, event: Event, segments: Union[MessageSegment, List]) -> None:
    """
        自动判断message是 List 还是单个，然后发送{转发}，允许发送群和个人
    :param bot:
    :param event:
    :param segments:
    :return:
    """
    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=segments)
    else:
        await bot.send_private_forward_msg(user_id=event.user_id, messages=segments)


async def send_both(bot: Bot, event: Event, segments: MessageSegment) -> None:
    """
        自动判断message是 List 还是单个，发送{单个消息}，允许发送群和个人
    :param bot:
    :param event:
    :param segments:
    :return:
    """
    if isinstance(event, GroupMessageEvent):
        await bot.send_group_msg(group_id=event.group_id, message=Message(segments))
    elif isinstance(event, PrivateMessageEvent):
        await bot.send_private_msg(user_id=event.user_id, message=Message(segments))


async def upload_both(bot: Bot, event: Event, file_path: str, name: str) -> None:
    """
        上传文件，不限于群和个人
    :param bot:
    :param event:
    :param file_path:
    :param name:
    :return:
    """
    if isinstance(event, GroupMessageEvent):
        # 上传群文件
        await bot.upload_group_file(group_id=event.group_id, file=file_path, name=name)
    elif isinstance(event, PrivateMessageEvent):
        # 上传私聊文件
        await bot.upload_private_file(user_id=event.user_id, file=file_path, name=name)


def get_id_both(event: MessageEvent):
    if isinstance(event, GroupMessageEvent):
        return event.group_id
    elif isinstance(event, PrivateMessageEvent):
        return event.user_id


@DeprecationWarning
async def auto_video_send(event: Event, data_path: Path):
    """
    自动判断视频类型并进行发送，支持群发和私发
    :param event:
    :param data_path:
    :return:
    """
    try:
        bot: Bot = cast(Bot, current_bot.get())

        # 如果data以"http"开头，先下载视频
        if data_path is not None and data_path.startswith("http"):
            data_path = await download_video(data_path)

        # 检测文件大小
        file_size_in_mb = get_file_size_mb(data_path)
        # 如果视频大于 100 MB 自动转换为群文件
        if file_size_in_mb > VIDEO_MAX_MB:
            await bot.send(event, Message(
                f"当前解析文件 {file_size_in_mb} MB 大于 {VIDEO_MAX_MB} MB，尝试改用文件方式发送，请稍等..."))
            await upload_both(bot, event, data_path, data_path.split('/')[-1])
            return
        # 根据事件类型发送不同的消息
        await send_both(bot, event, MessageSegment.video(f'file://{data_path}'))
    except Exception as e:
        logger.error(f"解析发送出现错误，具体为\n{e}")


async def get_video_seg(data_path: Path) -> MessageSegment:
    seg: MessageSegment
    try:
        # 如果data以"http"开头，先下载视频
        if data_path is not None and data_path.startswith("http"):
            data_path = await download_video(data_path)

        # 检测文件大小
        file_size_in_mb = get_file_size_mb(data_path)

        # 如果视频大于 100 MB 自动转换为群文件, 先忽略
        if file_size_in_mb > VIDEO_MAX_MB:
            # seg = Message(f"当前解析文件 {file_size_in_mb} MB 大于 {VIDEO_MAX_MB} MB, 取消发送")
            seg = get_file_seg(data_path)
        seg = MessageSegment.video(data_path)
    except Exception as e:
        logger.error(f"下载视频失败，具体错误为\n{e}")
        seg = Message(f"下载视频失败，具体错误为\n{e}")
    finally:
        return seg
    
def get_file_seg(data_path: Path) -> MessageSegment:
    return MessageSegment(type = "file", data = {
        "name": data_path.name, # [发] [选]
        "file": data_path.absolute(),
        "path": "empty", #  [收]
        "url": "empty", #  [收]
        "file_id": "empty", #  [收]
        "file_size": "empty", #  [收]
        "file_unique": "empty" #  [收]
  })
