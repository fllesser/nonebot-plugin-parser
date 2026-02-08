class ParseException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DownloadException(ParseException):
    """下载异常"""

    def __init__(self, message: str | None = None):
        super().__init__(message or "媒体下载失败")


class IgnoreException(ParseException):
    """可忽略异常"""

    def __init__(self, message: str | None = None):
        super().__init__(message or "可忽略异常")


class TipException(ParseException):
    """提示异常"""
