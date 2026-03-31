"""Instagram Reels scraper."""
import re
import json
from typing import Optional, List
from datetime import datetime
from ..utils.models import VideoMetadata, Platform, ScrapedVideoCollection
from .base import BaseScraper


class InstagramScraper(BaseScraper):
    """Scraper for Instagram Reels."""
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.base_url = "https://www.instagram.com"
    
    @property
    def platform(self) -> Platform:
        return Platform.INSTAGRAM
    
    async def search_by_hashtag(
        self, 
        hashtag: str, 
        min_likes: int = 100000,
        min_views: int = 1000000,
        max_results: int = 50
    ) -> ScrapedVideoCollection:
        """Search Instagram Reels by hashtag with engagement filters."""
        collection = ScrapedVideoCollection()
        
        # Note: This is a simplified implementation
        # In production, you'd use Instagram's API or more sophisticated scraping
        # with proper authentication and rate limiting
        
        search_url = f"{self.base_url}/explore/tags/{hashtag.replace('#', '')}/?__a=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        content = await self.fetch_url(search_url, headers)
        if not content:
            return collection
        
        try:
            data = json.loads(content)
            # Extract video posts from the response
            # This is a simplified extraction - actual implementation would need
            # to handle Instagram's complex data structure
            edges = data.get('graphql', {}).get('hashtag', {}).get('edge_hashtag_to_media', {}).get('edges', [])
            
            for edge in edges[:max_results]:
                node = edge.get('node', {})
                
                # Skip non-video content
                if not node.get('is_video', False):
                    continue
                
                likes = node.get('edge_liked_by', {}).get('count', 0)
                views = node.get('video_view_count', 0)
                
                # Apply filters
                if likes >= min_likes and views >= min_views:
                    metadata = VideoMetadata(
                        url=f"{self.base_url}/p/{node.get('shortcode', '')}/",
                        platform=self.platform,
                        video_id=node.get('shortcode', ''),
                        title=node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', '')[:100],
                        description=node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                        author=node.get('owner', {}).get('username', 'unknown'),
                        likes=likes,
                        views=views,
                        comments=node.get('edge_media_to_comment', {}).get('count', 0),
                        hashtags=[hashtag],
                        duration=node.get('video_duration'),
                        thumbnail_url=node.get('display_url'),
                        created_at=datetime.fromtimestamp(node.get('taken_at_timestamp', 0)) if node.get('taken_at_timestamp') else None
                    )
                    collection.add_video(metadata)
        
        except Exception as e:
            print(f"Error parsing Instagram data: {e}")
        
        return collection
    
    async def get_video_metadata(self, video_url: str) -> Optional[VideoMetadata]:
        """Get metadata for a specific Instagram Reel."""
        # Extract shortcode from URL
        match = re.search(r'/p/([A-Za-z0-9_-]+)/', video_url)
        if not match:
            return None
        
        shortcode = match.group(1)
        url = f"{self.base_url}/p/{shortcode}/?__a=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        content = await self.fetch_url(url, headers)
        if not content:
            return None
        
        try:
            data = json.loads(content)
            node = data.get('graphql', {}).get('shortcode_media', {})
            
            if not node:
                return None
            
            return VideoMetadata(
                url=video_url,
                platform=self.platform,
                video_id=shortcode,
                title=node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', '')[:100],
                description=node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                author=node.get('owner', {}).get('username', 'unknown'),
                likes=node.get('edge_liked_by', {}).get('count', 0),
                views=node.get('video_view_count', 0),
                comments=node.get('edge_media_to_comment', {}).get('count', 0),
                duration=node.get('video_duration'),
                thumbnail_url=node.get('display_url'),
                created_at=datetime.fromtimestamp(node.get('taken_at_timestamp', 0)) if node.get('taken_at_timestamp') else None
            )
        except Exception as e:
            print(f"Error getting Instagram video metadata: {e}")
            return None
    
    async def download_video(self, video_url: str, save_path: str) -> bool:
        """Download Instagram Reel video."""
        # Get video page to extract video URL
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        content = await self.fetch_url(video_url, headers)
        if not content:
            return False
        
        # Extract video URL from page (simplified - actual implementation needs better parsing)
        video_match = re.search(r'"video_url":"([^"]+)"', content)
        if not video_match:
            return False
        
        video_download_url = video_match.group(1).replace('\\u002F', '/')
        
        # Download the actual video
        if self.session:
            try:
                async with self.session.get(video_download_url, headers=headers) as response:
                    response.raise_for_status()
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
                    return True
            except Exception as e:
                print(f"Error downloading Instagram video: {e}")
                return False
        
        return False
