from pathlib import Path

from nonebot_plugin_alconna import Image, Text, UniMessage
from nonebot_plugin_htmlkit import template_to_pic

from nonebot_plugin_resolver2.config import NEED_FORWARD
from nonebot_plugin_resolver2.matchers.helper import UniHelper, current_bot
from nonebot_plugin_resolver2.parsers import ParseResult
from nonebot_plugin_resolver2.renders.base import BaseRenderer


class Renderer(BaseRenderer):
    @staticmethod
    async def render_messages(result: ParseResult) -> list[UniMessage]:
        str_content = "\n".join(item for item in result.contents if isinstance(item, str))

        messages = []

        image = await template_to_pic(
            str(Path(__file__).parent / "templates"),
            "weibo.html.jinja",
            templates={"result": result, "str_content": str_content},
        )
        if image:
            messages.append(UniMessage([Image(raw=image)]))

        separate_segs, forwardable_segs = result.convert_segs()
        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
            if NEED_FORWARD or len(forwardable_segs) > 4:
                # 使用转发消息
                bot = current_bot.get()
                forward_msg = UniHelper.construct_forward_message(bot.self_id, forwardable_segs)
                messages.append(UniMessage([forward_msg]))
            else:
                # 直接发送
                forwardable_segs[:-1] = [
                    Text(seg + "\n") if isinstance(seg, str) else seg for seg in forwardable_segs[:-1]
                ]
                # 单条消息
                single_msg = UniMessage()
                for seg in forwardable_segs:
                    single_msg += seg
                messages.append(single_msg)

        # 处理必须单独发送的消息段
        if separate_segs:
            messages.extend(UniMessage(seg) for seg in separate_segs)

        return messages
