from typing import Final

import httpx

COMMON_HEADER: Final[dict[str, str]] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/55.0.2883.87 UBrowser/6.2.4098.3 Safari/537.36"
}

IOS_HEADER: Final[dict[str, str]] = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.6 Mobile/15E148 Safari/604.1 Edg/132.0.0.0"
}

ANDROID_HEADER: Final[dict[str, str]] = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/132.0.0.0 Mobile Safari/537.36 Edg/132.0.0.0"
}

# 解析列表文件名
DISABLED_GROUPS: Final[str] = "disable_group_list.json"

COMMON_TIMEOUT: Final[httpx.Timeout] = httpx.Timeout(connect=15.0, read=20.0, write=10.0, pool=10.0)

DOWNLOAD_TIMEOUT: Final[httpx.Timeout] = httpx.Timeout(connect=15.0, read=240.0, write=10.0, pool=10.0)
