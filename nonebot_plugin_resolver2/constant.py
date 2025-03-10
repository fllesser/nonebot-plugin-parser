from typing import Final

"""
通用头请求
"""
COMMON_HEADER: Final[dict[str, str]] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 "
    "UBrowser/6.2.4098.3 Safari/537.36"
}

"""
视频最大大小（MB）
"""
VIDEO_MAX_MB: Final[int] = 100

# 解析列表文件名
DISABLE_GROUPS: Final[str] = "disable_group_list.json"
