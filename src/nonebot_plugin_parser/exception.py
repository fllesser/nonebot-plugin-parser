class ParseException(Exception):
    """异常基类"""

    def __init__(self, message: str):
        self.message = message


class DownloadException(ParseException):
    """下载异常"""

    def __init__(self, message: str | None = None):
        self.message = message or "媒体下载失败"


class DownloadLimitException(DownloadException):
    """下载超过限制异常"""

    def __init__(self):
        raise NotImplementedError


class SizeLimitException(DownloadLimitException):
    """下载大小超过限制异常"""

    def __init__(self):
        self.message = "媒体大小超过配置限制，取消下载"


class DurationLimitException(DownloadLimitException):
    """下载时长超过限制异常"""

    def __init__(self):
        self.message = "媒体时长超过配置限制，取消下载"
