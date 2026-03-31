"""Data models for video processing pipeline."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class Platform(str, Enum):
    """Supported social media platforms."""
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    DOUYIN = "douyin"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    THREADS = "threads"


class VideoStatus(str, Enum):
    """Video processing status."""
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    PROCESSING = "processing"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    UPLOADED = "uploaded"
    FAILED = "failed"


class VideoMetadata(BaseModel):
    """Video metadata from scraping."""
    url: str
    platform: Platform
    video_id: str
    title: str
    description: str
    author: str
    likes: int = Field(ge=0)
    views: int = Field(ge=0)
    shares: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    hashtags: List[str] = Field(default_factory=list)
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class AIReviewResult(BaseModel):
    """AI review results for a video."""
    video_id: str
    is_approved: bool
    score: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    viral_potential: str = Field(default="unknown")  # low, medium, high
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Optional[Dict[str, Any]] = None


class ProcessedVideo(BaseModel):
    """Processed video ready for upload."""
    metadata: VideoMetadata
    local_path: str
    ai_review: Optional[AIReviewResult] = None
    status: VideoStatus = Field(default=VideoStatus.PENDING)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    upload_results: Dict[Platform, Dict[str, Any]] = Field(default_factory=dict)


class ScrapedVideoCollection(BaseModel):
    """Collection of scraped videos."""
    videos: List[VideoMetadata] = Field(default_factory=list)
    total_count: int = Field(default=0)
    filtered_count: int = Field(default=0)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_video(self, video: VideoMetadata) -> None:
        """Add a video to the collection."""
        self.videos.append(video)
        self.total_count += 1
    
    def filter_by_criteria(self, min_likes: int, min_views: int) -> List[VideoMetadata]:
        """Filter videos by engagement criteria."""
        filtered = [
            v for v in self.videos 
            if v.likes >= min_likes and v.views >= min_views
        ]
        self.filtered_count = len(filtered)
        return filtered
