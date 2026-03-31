"""Base scraper interface and common utilities."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import aiohttp
from aiohttp import ClientSession, TCPConnector
import asyncio
from datetime import datetime
import backoff
from ..utils.models import VideoMetadata, Platform, ScrapedVideoCollection
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class RateLimitError(ScraperError):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(ScraperError):
    """Raised when authentication fails."""
    pass


class BaseScraper(ABC):
    """Abstract base class for social media scrapers."""
    
    def __init__(
        self, 
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_delay: float = 1.0,
        max_concurrent_requests: int = 5
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self.max_concurrent_requests = max_concurrent_requests
        self.session: Optional[ClientSession] = None
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def __aenter__(self):
        connector = TCPConnector(
            limit=self.max_concurrent_requests,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        self.session = ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=connector,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        logger.info(f"{self.platform.value} scraper initialized with {self.max_concurrent_requests} concurrent requests")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            logger.info(f"{self.platform.value} scraper session closed")
    
    @abstractmethod
    async def search_by_hashtag(self, hashtag: str, **kwargs) -> ScrapedVideoCollection:
        """Search videos by hashtag."""
        pass
    
    @abstractmethod
    async def get_video_metadata(self, video_url: str) -> Optional[VideoMetadata]:
        """Get metadata for a specific video."""
        pass
    
    @abstractmethod
    async def download_video(self, video_url: str, save_path: str) -> bool:
        """Download video to local storage."""
        pass
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform this scraper handles."""
        pass
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.utcnow() - self._last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = datetime.utcnow()
        self._request_count += 1
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        giveup=lambda e: isinstance(e, (AuthenticationError, RateLimitError))
    )
    async def fetch_url(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        use_rate_limit: bool = True
    ) -> Optional[str]:
        """Fetch URL content with error handling and retries."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        if use_rate_limit:
            async with self._semaphore:
                await self._rate_limit()
                try:
                    async with self.session.get(url, headers=headers or {}) as response:
                        if response.status == 429:
                            raise RateLimitError(f"Rate limited for {url}")
                        if response.status == 401:
                            raise AuthenticationError(f"Authentication failed for {url}")
                        response.raise_for_status()
                        content = await response.text()
                        logger.debug(f"Successfully fetched {url} ({len(content)} bytes)")
                        return content
                except Exception as e:
                    if not isinstance(e, (AuthenticationError, RateLimitError)):
                        logger.warning(f"Error fetching {url}: {e}")
                    raise
        else:
            async with self.session.get(url, headers=headers or {}) as response:
                response.raise_for_status()
                return await response.text()
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        giveup=lambda e: isinstance(e, (AuthenticationError, RateLimitError))
    )
    async def fetch_json(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        use_rate_limit: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Fetch JSON data from URL with error handling and retries."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        if use_rate_limit:
            async with self._semaphore:
                await self._rate_limit()
                try:
                    async with self.session.get(url, headers=headers or {}) as response:
                        if response.status == 429:
                            raise RateLimitError(f"Rate limited for {url}")
                        if response.status == 401:
                            raise AuthenticationError(f"Authentication failed for {url}")
                        response.raise_for_status()
                        data = await response.json()
                        logger.debug(f"Successfully fetched JSON from {url}")
                        return data
                except Exception as e:
                    if not isinstance(e, (AuthenticationError, RateLimitError)):
                        logger.warning(f"Error fetching JSON from {url}: {e}")
                    raise
        else:
            async with self.session.get(url, headers=headers or {}) as response:
                response.raise_for_status()
                return await response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            "platform": self.platform.value,
            "request_count": self._request_count,
            "last_request_time": self._last_request_time.isoformat() if self._last_request_time else None,
            "session_active": self.session is not None and not self.session.closed
        }
