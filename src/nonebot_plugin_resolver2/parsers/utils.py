import httpx

from ..constants import COMMON_HEADER


async def get_redirect_url(url: str, headers: dict[str, str] | None = None) -> str:
    """获取重定向后的URL"""
    headers = headers or COMMON_HEADER
    async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=False) as client:
        response = await client.get(url)
        if response.status_code >= 400:
            response.raise_for_status()
        return response.headers.get("Location", url)
