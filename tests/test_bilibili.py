import pytest
from nonebug import App

@pytest.mark.asyncio
async def test_bilibili(app: App):
    import time
    from nonebot_plugin_resolver2.matchers.bilibili import bilibili
    from nonebot.adapters.onebot.v11 import Adapter, Bot, MessageEvent, Message
    
    event = MessageEvent(
        time=int(time.time()),
        self_id=123456789,
        post_type="message",
        sub_type="normal",
        message_type="group",
        message_id=12354678,
        raw_message="BV1584y167sD 40",
        message=Message("BV1584y167sD 40"),
        user_id=1234567890,
        group_id=12345678,
        sender={},
        font=15
    )
    async with app.test_matcher(bilibili) as ctx:
        adapter = nonebot.get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, '解析 | 哔哩哔哩 - 视频', result=None)
        ctx.should_call_send(event, None, result=None)
        ctx.should_call_send(event, None, result=None)
        ctx.should_finished(bilibili)
        
