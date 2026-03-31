"""Utility functions package initialization."""
from .logger import setup_logger
from .models import (
    Platform, 
    VideoStatus, 
    VideoMetadata, 
    AIReviewResult, 
    ProcessedVideo,
    ScrapedVideoCollection
)

__all__ = [
    "setup_logger",
    "Platform",
    "VideoStatus",
    "VideoMetadata",
    "AIReviewResult",
    "ProcessedVideo",
    "ScrapedVideoCollection"
]
