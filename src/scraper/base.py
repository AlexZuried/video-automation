import httpx
import asyncio
from typing import List, Dict, Optional
from loguru import logger
import backoff

class BaseScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
            }
        )

    @backoff.on_exception(backoff.expo, httpx.RequestError, max_tries=3)
    async def fetch_url(self, url: str) -> Optional[str]:
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

    async def scrape_hashtag(self, hashtag: str, limit: int = 10) -> List[Dict]:
        raise NotImplementedError
