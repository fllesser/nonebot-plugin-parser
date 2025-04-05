from collections.abc import Callable
from functools import wraps

from nonebot import logger
from nonebot.matcher import Matcher


class DownloadException(Exception):
    """下载异常"""

    pass


class ParseException(Exception):
    """解析异常"""

    pass


def handle_exception(matcher: type[Matcher], error_message: str | None = None):
    """处理 matcher 中的 DownloadException 和 ParseException 异常的装饰器

    Args:
        matcher: 需要处理的 matcher 类型
        error_message: 自定义错误消息
        reply_message: 是否回复消息
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (ParseException, DownloadException) as e:
                logger.warning(f"{matcher.module_name}: {e}")
                msg = error_message or str(e)
                await matcher.finish(msg, reply_message=True)

        return wrapper

    return decorator
