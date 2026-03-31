"""Test suite for video automation pipeline."""
import pytest
from pathlib import Path


class TestConfig:
    """Tests for configuration module."""
    
    def test_load_config(self):
        """Test configuration loading."""
        from src.config import load_config
        
        config = load_config()
        
        assert config.scraper.min_likes >= 0
        assert config.scraper.min_views >= 0
        assert config.scraper.max_videos_per_run >= 1
    
    def test_scraper_config_defaults(self):
        """Test scraper configuration defaults."""
        from src.config.settings import ScraperConfig
        
        config = ScraperConfig()
        
        assert config.min_likes == 100000
        assert config.min_views == 1000000
        assert config.max_videos_per_run == 50


class TestModels:
    """Tests for data models."""
    
    def test_video_metadata_creation(self):
        """Test VideoMetadata model creation."""
        from src.utils import VideoMetadata, Platform
        
        video = VideoMetadata(
            url="https://example.com/video/123",
            platform=Platform.INSTAGRAM,
            video_id="123",
            title="Test Video",
            description="Test Description",
            author="test_user",
            likes=150000,
            views=1500000
        )
        
        assert video.platform == Platform.INSTAGRAM
        assert video.likes == 150000
        assert video.views == 1500000
    
    def test_scraped_collection_filtering(self):
        """Test video collection filtering."""
        from src.utils import ScrapedVideoCollection, VideoMetadata, Platform
        
        collection = ScrapedVideoCollection()
        
        # Add videos with different engagement levels
        for i in range(5):
            video = VideoMetadata(
                url=f"https://example.com/video/{i}",
                platform=Platform.TIKTOK,
                video_id=str(i),
                title=f"Video {i}",
                description="",
                author="user",
                likes=100000 * (i + 1),
                views=1000000 * (i + 1)
            )
            collection.add_video(video)
        
        # Filter by criteria
        filtered = collection.filter_by_criteria(min_likes=300000, min_views=3000000)
        
        assert len(filtered) == 3  # Videos 2, 3, 4 should pass
        assert collection.filtered_count == 3


class TestScraper:
    """Tests for scraper modules."""
    
    def test_instagram_scraper_initialization(self):
        """Test Instagram scraper initialization."""
        from src.scraper.instagram import InstagramScraper
        from src.utils import Platform
        
        scraper = InstagramScraper()
        
        assert scraper.platform == Platform.INSTAGRAM
        assert scraper.timeout == 30
    
    def test_tiktok_scraper_initialization(self):
        """Test TikTok scraper initialization."""
        from src.scraper.tiktok import TikTokScraper
        from src.utils import Platform
        
        scraper = TikTokScraper()
        
        assert scraper.platform == Platform.TIKTOK
    
    def test_get_scraper_factory(self):
        """Test scraper factory function."""
        from src.scraper import get_scraper
        from src.utils import Platform
        
        instagram_scraper = get_scraper("instagram")
        tiktok_scraper = get_scraper("tiktok")
        
        assert instagram_scraper.platform == Platform.INSTAGRAM
        assert tiktok_scraper.platform == Platform.TIKTOK
    
    def test_get_scraper_invalid_platform(self):
        """Test scraper factory with invalid platform."""
        from src.scraper import get_scraper
        
        with pytest.raises(ValueError):
            get_scraper("invalid_platform")


class TestUploader:
    """Tests for uploader modules."""
    
    def test_twitter_uploader_configuration(self):
        """Test Twitter uploader configuration check."""
        from src.uploader.twitter import TwitterUploader
        
        # Unconfigured
        uploader = TwitterUploader()
        assert not uploader.is_configured()
        
        # Configured
        uploader = TwitterUploader(
            api_key="test",
            api_secret="test",
            access_token="test",
            access_token_secret="test"
        )
        assert uploader.is_configured()
    
    def test_youtube_uploader_configuration(self):
        """Test YouTube uploader configuration check."""
        from src.uploader.youtube import YouTubeUploader
        
        uploader = YouTubeUploader(api_key="test_key")
        assert uploader.is_configured()
        
        uploader = YouTubeUploader()
        assert not uploader.is_configured()
    
    def test_get_uploader_factory(self):
        """Test uploader factory function."""
        from src.uploader import get_uploader
        from src.utils import Platform
        
        uploader = get_uploader("twitter", {
            "api_key": "test",
            "api_secret": "test",
            "access_token": "test",
            "access_token_secret": "test"
        })
        
        assert uploader.platform == Platform.TWITTER


class TestProcessor:
    """Tests for processor modules."""
    
    def test_video_reviewer_initialization(self):
        """Test VideoReviewer initialization."""
        from src.processor import VideoReviewer
        
        reviewer = VideoReviewer(api_key="test_key")
        
        assert reviewer.model == "gpt-4-turbo-preview"
        
        reviewer_custom = VideoReviewer(api_key="test_key", model="gpt-4")
        assert reviewer_custom.model == "gpt-4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
