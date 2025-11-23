class ParseException(Exception):
    """异常基类"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TipException(ParseException):
    """提示异常"""

    pass


class DownloadException(ParseException):
    """下载异常"""

    def __init__(self, message: str | None = None):
        super().__init__(message or "媒体下载失败")


class DownloadLimitException(DownloadException):
    """下载超过限制异常"""

    pass


class SizeLimitException(DownloadLimitException):
    """下载大小超过限制异常"""

    def __init__(self):
        super().__init__("媒体大小超过配置限制，取消下载")


class DurationLimitException(DownloadLimitException):
    """下载时长超过限制异常"""

    def __init__(self):
        super().__init__("媒体时长超过配置限制，取消下载")


class ZeroSizeException(DownloadException):
    """下载大小为 0 异常"""

    def __init__(self):
        super().__init__("媒体大小为 0, 取消下载")
