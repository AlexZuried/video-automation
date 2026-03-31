"""Base scraper interface and common utilities."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import aiohttp
from ..utils.models import VideoMetadata, Platform, ScrapedVideoCollection


class BaseScraper(ABC):
    """Abstract base class for social media scrapers."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
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
    
    async def fetch_url(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Fetch URL content with error handling."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(url, headers=headers or {}) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    async def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Fetch JSON data from URL with error handling."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(url, headers=headers or {}) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            print(f"Error fetching JSON from {url}: {e}")
            return None
