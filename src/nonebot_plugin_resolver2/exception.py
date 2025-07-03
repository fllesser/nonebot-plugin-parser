from collections.abc import Callable
from functools import wraps

from nonebot.internal.matcher import current_matcher


class DownloadException(Exception):
    """下载异常"""

    pass


class ParseException(Exception):
    """解析异常"""

    pass


def handle_exception(error_message: str | None = None):
    """处理 matcher 中的 DownloadException 和 ParseException 异常的装饰器

    Args:
        matcher: 需要处理的 matcher 类型
        error_message: 自定义错误消息
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (ParseException, DownloadException) as e:
                matcher = current_matcher.get()
                # logger.warning(f"{matcher.module_name}: {e}")
                await matcher.finish(error_message or str(e))

        return wrapper

    return decorator
