"""Uploader package initialization."""
from .base import BaseUploader
from .twitter import TwitterUploader
from .youtube import YouTubeUploader
from .instagram import InstagramUploader
from .tiktok import TikTokUploader
from .threads import ThreadsUploader
from .manager import UploadManager

__all__ = [
    "BaseUploader",
    "TwitterUploader",
    "YouTubeUploader",
    "InstagramUploader",
    "TikTokUploader",
    "ThreadsUploader",
    "UploadManager"
]


def get_uploader(platform: str, config: dict):
    """Factory function to get uploader by platform name."""
    uploaders = {
        "twitter": lambda: TwitterUploader(**config),
        "youtube": lambda: YouTubeUploader(**config),
        "instagram": lambda: InstagramUploader(**config),
        "tiktok": lambda: TikTokUploader(**config),
        "threads": lambda: ThreadsUploader(**config)
    }
    
    platform_lower = platform.lower()
    if platform_lower not in uploaders:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(uploaders.keys())}")
    
    return uploaders[platform_lower]()
