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


class ParseException(ResolverException):
    """解析异常"""

    pass
