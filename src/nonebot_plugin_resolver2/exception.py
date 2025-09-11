from collections.abc import Callable
from functools import wraps

from nonebot.internal.matcher import current_matcher


class ResolverException(Exception):
    """插件异常 base class"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DownloadException(ResolverException):
    """下载异常"""

    pass


class DownloadSizeLimitException(DownloadException):
    """下载大小超过限制异常"""

    def __init__(self):
        self.message = "媒体大小超过配置限制，取消下载"
        super().__init__(self.message)


class DownloadFailedException(DownloadException):
    """下载失败异常"""

    def __init__(self):
        self.message = "媒体下载失败"
        super().__init__(self.message)


class ParseException(ResolverException):
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
            except ResolverException as e:
                matcher = current_matcher.get()
                await matcher.finish(error_message or e.message)

        return wrapper

    return decorator
