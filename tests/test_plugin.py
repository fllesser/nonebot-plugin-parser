# from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
# from nonebug import App
# import pytest


# def make_onebot_msg(message: Message) -> GroupMessageEvent:
#     from time import time

#     from nonebot.adapters.onebot.v11.event import Sender

#     event = GroupMessageEvent(
#         time=int(time()),
#         sub_type="normal",
#         self_id=123456,
#         post_type="message",
#         message_type="group",
#         message_id=12345623,
#         user_id=1234567890,
#         group_id=1234567890,
#         raw_message=message.extract_plain_text(),
#         message=message,
#         original_message=message,
#         sender=Sender(),
#         font=123456,
#     )
#     return event


# @pytest.mark.asyncio
# async def test_pip(app: App):
#     import nonebot
#     from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

#     event = make_onebot_msg(Message("pip install nonebot2"))
#     try:
#         from nonebot_plugin_template import pip  #
#     except ImportError:
#         pytest.skip("nonebot_plugin_template.pip not found")

#     async with app.test_matcher(pip) as ctx:
#         adapter = nonebot.get_adapter(OnebotV11Adapter)
#         bot = ctx.create_bot(base=Bot, adapter=adapter)
#         ctx.receive_event(bot, event)
#         ctx.should_call_send(event, Message("nonebot2"), result=None, bot=bot)
#         ctx.should_finished()
