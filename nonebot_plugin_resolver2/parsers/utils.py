async def get_redirect_url(url: str, headers: dict[str, str] | None = None) -> str:
    import aiohttp

    from .data import COMMON_HEADER

    """获取重定向后的URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers or COMMON_HEADER, allow_redirects=False, ssl=False) as response:
            response.raise_for_status()
            return response.headers.get("Location", url)
