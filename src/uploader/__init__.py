"""Uploader modules package initialization."""
from .twitter import TwitterUploader
from .youtube import YouTubeUploader
from .instagram import InstagramUploader
from .tiktok import TikTokUploader
from .threads import ThreadsUploader
from .base import BaseUploader
from ..utils.models import Platform
from typing import Dict, Any, Optional


def get_uploader(platform_name: str, config: Optional[Dict[str, Any]] = None) -> BaseUploader:
    """Factory function to get uploader by platform name.
    
    Args:
        platform_name: Name of the platform
        config: Optional configuration dictionary for the uploader
        
    Returns:
        Appropriate uploader instance
        
    Raises:
        ValueError: If platform is not supported
    """
    if config is None:
        config = {}
    
    uploaders = {
        "twitter": lambda: TwitterUploader(
            api_key=config.get("api_key"),
            api_secret=config.get("api_secret"),
            access_token=config.get("access_token"),
            access_token_secret=config.get("access_token_secret")
        ),
        "youtube": lambda: YouTubeUploader(api_key=config.get("api_key")),
        "instagram": lambda: InstagramUploader(
            username=config.get("username"),
            password=config.get("password")
        ),
        "tiktok": lambda: TikTokUploader(
            client_key=config.get("client_key"),
            client_secret=config.get("client_secret")
        ),
        "threads": lambda: ThreadsUploader(access_token=config.get("access_token")),
    }
    
    platform_lower = platform_name.lower()
    if platform_lower not in uploaders:
        raise ValueError(f"Unsupported platform: {platform_name}. Supported: {list(uploaders.keys())}")
    
    return uploaders[platform_lower]()


__all__ = [
    "TwitterUploader", 
    "YouTubeUploader", 
    "InstagramUploader",
    "TikTokUploader",
    "ThreadsUploader",
    "BaseUploader",
    "get_uploader"
]
