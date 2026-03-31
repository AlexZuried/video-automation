"""TikTok video scraper."""
import re
import json
from typing import Optional, List
from datetime import datetime
from ..utils.models import VideoMetadata, Platform, ScrapedVideoCollection
from .base import BaseScraper


class TikTokScraper(BaseScraper):
    """Scraper for TikTok videos."""
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.base_url = "https://www.tiktok.com"
    
    @property
    def platform(self) -> Platform:
        return Platform.TIKTOK
    
    async def search_by_hashtag(
        self, 
        hashtag: str, 
        min_likes: int = 100000,
        min_views: int = 1000000,
        max_results: int = 50
    ) -> ScrapedVideoCollection:
        """Search TikTok videos by hashtag with engagement filters."""
        collection = ScrapedVideoCollection()
        
        # Note: This is a simplified implementation
        # TikTok has strict anti-scraping measures
        # In production, use official TikTok API
        
        hashtag_clean = hashtag.replace('#', '')
        search_url = f"{self.base_url}/tag/{hashtag_clean}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.base_url
        }
        
        content = await self.fetch_url(search_url, headers)
        if not content:
            return collection
        
        # Extract video data from page (simplified)
        # Actual implementation would need to handle TikTok's complex structure
        video_pattern = r'"webVideoUrl":"([^"]+)"'
        matches = re.findall(video_pattern, content)
        
        for video_url in matches[:max_results]:
            try:
                metadata = await self.get_video_metadata(video_url)
                if metadata and metadata.likes >= min_likes and metadata.views >= min_views:
                    metadata.hashtags = [hashtag]
                    collection.add_video(metadata)
            except Exception as e:
                print(f"Error processing TikTok video: {e}")
                continue
        
        return collection
    
    async def get_video_metadata(self, video_url: str) -> Optional[VideoMetadata]:
        """Get metadata for a specific TikTok video."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        content = await self.fetch_url(video_url, headers)
        if not content:
            return None
        
        try:
            # Extract video ID from URL
            video_id_match = re.search(r'/video/(\d+)', video_url)
            video_id = video_id_match.group(1) if video_id_match else 'unknown'
            
            # Extract metadata using regex patterns (simplified)
            title_match = re.search(r'"desc":"([^"]+)"', content)
            author_match = re.search(r'"uniqueId":"([^"]+)"', content)
            likes_match = re.search(r'"diggCount":(\d+)', content)
            views_match = re.search(r'"playCount":(\d+)', content)
            comments_match = re.search(r'"commentCount":(\d+)', content)
            
            title = title_match.group(1) if title_match else ''
            if title:
                # Decode HTML entities
                title = title.replace('\\u002F', '/').replace('\\"', '"')
            
            return VideoMetadata(
                url=video_url,
                platform=self.platform,
                video_id=video_id,
                title=title[:100] if title else 'TikTok Video',
                description=title or '',
                author=author_match.group(1) if author_match else 'unknown',
                likes=int(likes_match.group(1)) if likes_match else 0,
                views=int(views_match.group(1)) if views_match else 0,
                comments=int(comments_match.group(1)) if comments_match else 0,
                hashtags=[],
                created_at=datetime.utcnow()
            )
        except Exception as e:
            print(f"Error getting TikTok video metadata: {e}")
            return None
    
    async def download_video(self, video_url: str, save_path: str) -> bool:
        """Download TikTok video without watermark if possible."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        content = await self.fetch_url(video_url, headers)
        if not content:
            return False
        
        # Extract video URL (simplified - actual implementation needs better parsing)
        video_match = re.search(r'"playAddr":"([^"]+)"', content)
        if not video_match:
            return False
        
        video_download_url = video_match.group(1).replace('\\u002F', '/')
        
        # Download the video
        if self.session:
            try:
                async with self.session.get(video_download_url, headers=headers) as response:
                    response.raise_for_status()
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
                    return True
            except Exception as e:
                print(f"Error downloading TikTok video: {e}")
                return False
        
        return False
