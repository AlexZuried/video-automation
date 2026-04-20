"""Configuration management for video automation pipeline."""
import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Scraper configuration settings."""
    min_likes: int = Field(default=100000, ge=0)
    min_views: int = Field(default=1000000, ge=0)
    max_videos_per_run: int = Field(default=50, ge=1)
    max_concurrent_requests: int = Field(default=5, ge=1)
    retry_attempts: int = Field(default=3, ge=0)
    timeout_seconds: int = Field(default=30, ge=1)


class ProcessingConfig(BaseModel):
    """Processing configuration settings."""
    enable_deduplication: bool = Field(default=True)
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    enable_trend_prediction: bool = Field(default=True)


class UploadConfig(BaseModel):
    """Upload configuration settings."""
    batch_size: int = Field(default=10, ge=1)
    delay_between_uploads_seconds: int = Field(default=300, ge=0)
    platforms: list = Field(default_factory=lambda: ["instagram", "tiktok", "twitter", "youtube_shorts"])


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO")
    file: str = Field(default="logs/pipeline.log")


class AppConfig(BaseModel):
    """Main application configuration."""
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file. If None, uses default path.
        
    Returns:
        AppConfig object with loaded settings.
    """
    if config_path is None:
        # Look for config in standard locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "settings.yaml",
            Path("config") / "settings.yaml",
        ]
        for path in possible_paths:
            if path.exists():
                config_path = str(path)
                break
    
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return AppConfig(
            scraper=ScraperConfig(
                min_likes=data.get('scraping', {}).get('min_likes', 100000),
                min_views=data.get('scraping', {}).get('min_views', 1000000),
                max_videos_per_run=50,
                max_concurrent_requests=data.get('scraping', {}).get('max_concurrent_requests', 5),
                retry_attempts=data.get('scraping', {}).get('retry_attempts', 3),
                timeout_seconds=data.get('scraping', {}).get('timeout_seconds', 30),
            ),
            processing=ProcessingConfig(
                enable_deduplication=data.get('processing', {}).get('enable_deduplication', True),
                similarity_threshold=data.get('processing', {}).get('similarity_threshold', 0.85),
                enable_trend_prediction=data.get('processing', {}).get('enable_trend_prediction', True),
            ),
            upload=UploadConfig(
                batch_size=data.get('upload', {}).get('batch_size', 10),
                delay_between_uploads_seconds=data.get('upload', {}).get('delay_between_uploads_seconds', 300),
                platforms=data.get('upload', {}).get('platforms', ["instagram", "tiktok", "twitter", "youtube_shorts"]),
            ),
            logging=LoggingConfig(
                level=data.get('logging', {}).get('level', 'INFO'),
                file=data.get('logging', {}).get('file', 'logs/pipeline.log'),
            )
        )
    
    # Return defaults if no config file found
    return AppConfig()


__all__ = [
    "ScraperConfig",
    "ProcessingConfig", 
    "UploadConfig",
    "LoggingConfig",
    "AppConfig",
    "load_config"
]
