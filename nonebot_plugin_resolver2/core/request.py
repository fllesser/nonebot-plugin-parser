import httpx

from tenacity import retry, stop_after_attempt, wait_fixed

# 定义重试策略：最多重试3次，每次等待2秒
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def fetch_data(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()  # 如果响应状态码不是200-299，抛出异常
        return response