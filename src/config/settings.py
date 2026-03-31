"""Configuration management using Pydantic."""
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class ScraperConfig(BaseModel):
    """Scraper configuration settings."""
    min_likes: int = Field(default=100000, ge=0)
    min_views: int = Field(default=1000000, ge=0)
    max_videos_per_run: int = Field(default=50, ge=1)
    hashtags: List[str] = Field(default_factory=list)
    timeout: int = Field(default=30, ge=5)


class AIConfig(BaseModel):
    """AI review configuration."""
    api_key: str = Field(default="")
    model: str = Field(default="gpt-4-turbo-preview")
    review_criteria: List[str] = Field(default=["high_quality", "engaging", "viral_potential"])
    max_retries: int = Field(default=3, ge=1)


class SocialMediaConfig(BaseModel):
    """Social media platform credentials."""
    twitter_api_key: Optional[str] = Field(default=None)
    twitter_api_secret: Optional[str] = Field(default=None)
    twitter_access_token: Optional[str] = Field(default=None)
    twitter_access_token_secret: Optional[str] = Field(default=None)
    
    youtube_api_key: Optional[str] = Field(default=None)
    
    tiktok_client_key: Optional[str] = Field(default=None)
    tiktok_client_secret: Optional[str] = Field(default=None)
    
    instagram_username: Optional[str] = Field(default=None)
    instagram_password: Optional[str] = Field(default=None)
    
    threads_access_token: Optional[str] = Field(default=None)


class AppConfig(BaseModel):
    """Main application configuration."""
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    social_media: SocialMediaConfig = Field(default_factory=SocialMediaConfig)
    
    video_cache_dir: str = Field(default="data/cache")
    video_output_dir: str = Field(default="data/videos")
    log_file: str = Field(default="data/logs/app.log")
    
    class Config:
        arbitrary_types_allowed = True


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    return AppConfig(
        scraper=ScraperConfig(
            min_likes=int(os.getenv("MIN_LIKES", 100000)),
            min_views=int(os.getenv("MIN_VIEWS", 1000000)),
            max_videos_per_run=int(os.getenv("MAX_VIDEOS_PER_RUN", 50)),
            hashtags=os.getenv("HASHTAGS", "").split(",") if os.getenv("HASHTAGS") else []
        ),
        ai=AIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("AI_MODEL", "gpt-4-turbo-preview"),
            review_criteria=os.getenv("REVIEW_CRITERIA", "high_quality,engaging,viral_potential").split(",")
        ),
        social_media=SocialMediaConfig(
            twitter_api_key=os.getenv("TWITTER_API_KEY"),
            twitter_api_secret=os.getenv("TWITTER_API_SECRET"),
            twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            twitter_access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
            tiktok_client_key=os.getenv("TIKTOK_CLIENT_KEY"),
            tiktok_client_secret=os.getenv("TIKTOK_CLIENT_SECRET"),
            instagram_username=os.getenv("INSTAGRAM_USERNAME"),
            instagram_password=os.getenv("INSTAGRAM_PASSWORD"),
            threads_access_token=os.getenv("THREADS_ACCESS_TOKEN")
        ),
        video_cache_dir=os.getenv("VIDEO_CACHE_DIR", "data/cache"),
        video_output_dir=os.getenv("VIDEO_OUTPUT_DIR", "data/videos"),
        log_file=os.getenv("LOG_FILE", "data/logs/app.log")
    )
