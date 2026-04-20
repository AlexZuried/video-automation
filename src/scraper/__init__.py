"""Scraper modules package initialization."""
from .instagram import InstagramScraper
from .tiktok import TikTokScraper
from .douyin import DouyinScraper
from .base import BaseScraper
from ..utils.models import Platform


def get_scraper(platform_name: str) -> BaseScraper:
    """Factory function to get scraper by platform name.
    
    Args:
        platform_name: Name of the platform ('instagram', 'tiktok', 'douyin')
        
    Returns:
        Appropriate scraper instance
        
    Raises:
        ValueError: If platform is not supported
    """
    scrapers = {
        "instagram": InstagramScraper,
        "tiktok": TikTokScraper,
        "douyin": DouyinScraper,
    }
    
    platform_lower = platform_name.lower()
    if platform_lower not in scrapers:
        raise ValueError(f"Unsupported platform: {platform_name}. Supported: {list(scrapers.keys())}")
    
    return scrapers[platform_lower]()


__all__ = ["InstagramScraper", "TikTokScraper", "DouyinScraper", "BaseScraper", "get_scraper"]
