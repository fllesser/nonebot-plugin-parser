from datetime import datetime
from pathlib import Path

from nonebot_plugin_alconna import Image, Text, UniMessage
from nonebot_plugin_htmlkit import template_to_pic

from ..config import NEED_FORWARD
from ..helper import UniHelper, current_bot
from ..parsers import ParseResult
from .base import BaseRenderer


def format_datetime(timestamp: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳为字符串"""
    return datetime.fromtimestamp(timestamp).strftime(fmt)


class Renderer(BaseRenderer):
    @staticmethod
    async def render_messages(result: ParseResult) -> list[UniMessage]:
        messages = []

        # 生成图片消息
        image = await template_to_pic(
            str(Path(__file__).parent / "templates"),
            "weibo.html.jinja",
            templates={"result": result},
            filters={"format_datetime": format_datetime},
        )
        image_message_segs = [
            Text(f"{result.author.name} 的微博\n" if result.author else "微博\n"),
            Image(raw=image),
        ]
        if result.repost and result.repost.url:
            image_message_segs.append(Text(f"\n源微博详情: {result.repost.url}"))
        if result.url:
            image_message_segs.append(Text(f"\n微博详情: {result.url}" if result.url else ""))
        messages.append(UniMessage(image_message_segs))

        # 将其他内容通过转发消息发送
        separate_segs, forwardable_segs = result.convert_segs()
        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
            if NEED_FORWARD or len(forwardable_segs) > 2:
                # 使用转发消息
                bot = current_bot.get()
                forward_msg = UniHelper.construct_forward_message(bot.self_id, forwardable_segs)
                messages.append(UniMessage([forward_msg]))
            else:
                forwardable_segs[:-1] = [seg + "\n" for seg in forwardable_segs[:-1]]
                # 单条消息
                single_msg = UniMessage()
                for seg in forwardable_segs:
                    single_msg += seg
                messages.append(single_msg)
        # 处理必须单独发送的消息段
        if separate_segs:
            messages.extend(UniMessage(seg) for seg in separate_segs)

        return messages
