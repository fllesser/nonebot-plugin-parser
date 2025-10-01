from http import cookiejar
from pathlib import Path


def save_cookies_with_netscape(cookies_str: str, file_path: Path, domain: str):
    """以 netscape 格式保存 cookies

    Args:
        cookies_str: cookies 字符串
        file_path: 保存的文件路径
        domain: 域名
    """
    # 创建 MozillaCookieJar 对象
    cj = cookiejar.MozillaCookieJar(file_path)

    # 从字符串创建 cookies 并添加到 MozillaCookieJar 对象
    for cookie in cookies_str.split(";"):
        name, value = cookie.strip().split("=", 1)
        cj.set_cookie(
            cookiejar.Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain="." + domain,
                domain_specified=True,
                domain_initial_dot=False,
                path="/",
                path_specified=True,
                secure=True,
                expires=0,
                discard=True,
                comment=None,
                comment_url=None,
                rest={"HttpOnly": ""},
                rfc2109=False,
            )
        )

    # 保存 cookies 到文件
    cj.save(ignore_discard=True, ignore_expires=True)


def ck2dict(cookies_str: str) -> dict[str, str]:
    """将 cookies 字符串转换为字典

    Args:
        cookies_str: cookies 字符串

    Returns:
        dict[str, str]: 字典
    """
    res = {}
    for cookie in cookies_str.split(";"):
        name, value = cookie.strip().split("=", 1)
        res[name] = value
    return res
