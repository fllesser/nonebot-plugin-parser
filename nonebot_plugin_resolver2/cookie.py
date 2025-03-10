from http import cookiejar
from pathlib import Path


def save_cookies_to_netscape(cookies_str: str, file: Path, domain: str):
    # 创建 MozillaCookieJar 对象
    cj = cookiejar.MozillaCookieJar(file)

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


def cookies_str_to_dict(cookies_str: str) -> dict[str, str]:
    res = {}
    for cookie in cookies_str.split(";"):
        name, value = cookie.strip().split("=", 1)
        res[name] = value
    return res
