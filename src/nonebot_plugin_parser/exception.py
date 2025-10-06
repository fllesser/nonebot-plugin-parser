class ParseException(Exception):
    """异常基类"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DownloadException(ParseException):
    """下载异常"""

    pass


class DownloadSizeLimitException(DownloadException):
    """下载大小超过限制异常"""

    def __init__(self):
        self.message = "媒体大小超过配置限制，取消下载"
        super().__init__(self.message)


class MultiException(ParseException):
    """多个异常"""

    def __init__(self, exceptions: list[ParseException]):
        self.exceptions = exceptions
        message = ",".join([e.message for e in exceptions])
        super().__init__(f"[{message}]")
