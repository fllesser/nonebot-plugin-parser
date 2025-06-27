async def get_redirect_url(url: str, headers: dict[str, str] | None = None) -> str:
    import httpx

    from .data import COMMON_HEADER

    """获取重定向后的URL"""
    async with httpx.AsyncClient(headers=headers or COMMON_HEADER, verify=False) as client:
        response = await client.get(url, follow_redirects=False)
        if response.status_code >= 400:
            response.raise_for_status()
        return response.headers.get("Location", url)
