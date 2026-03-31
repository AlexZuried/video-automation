"""Scraper package initialization."""
from .base import BaseScraper
from .instagram import InstagramScraper
from .tiktok import TikTokScraper
from .douyin import DouyinScraper

__all__ = [
    "BaseScraper",
    "InstagramScraper",
    "TikTokScraper", 
    "DouyinScraper"
]


def get_scraper(platform: str):
    """Factory function to get scraper by platform name."""
    scrapers = {
        "instagram": InstagramScraper,
        "tiktok": TikTokScraper,
        "douyin": DouyinScraper
    }
    
    platform_lower = platform.lower()
    if platform_lower not in scrapers:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(scrapers.keys())}")
    
    return scrapers[platform_lower]()
