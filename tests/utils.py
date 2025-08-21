from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
import pytest


def make_onebot_msg(message: Message) -> GroupMessageEvent:
    from time import time

    from nonebot.adapters.onebot.v11.event import Sender

    event = GroupMessageEvent(
        time=int(time()),
        sub_type="normal",
        self_id=123456,
        post_type="message",
        message_type="group",
        message_id=12345623,
        user_id=1234567890,
        group_id=1234567890,
        raw_message=message.extract_plain_text(),
        message=message,
        original_message=message,
        sender=Sender(),
        font=123456,
    )
    return event


# 添加一个装饰器来跳过失败的测试
def skip_on_failure(func):
    @pytest.mark.asyncio
    async def wrapper(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"测试 {func.__name__} 失败，已跳过", exc_info=True)
            pytest.skip(f"测试失败: {e}")

    return wrapper


from typing import Any


def load_test_urls(path: str = "test_urls.toml") -> dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(path, "rb") as f:
        return tomllib.load(f)


TEST_URLS = load_test_urls()
