"""Multi-platform video uploader manager."""
import asyncio
from typing import List, Dict, Any, Optional
from ..utils.models import ProcessedVideo, Platform, VideoStatus
from .base import BaseUploader


class UploadManager:
    """Manages uploading videos to multiple social media platforms."""
    
    def __init__(self, uploaders: List[BaseUploader]):
        self.uploaders = {uploader.platform: uploader for uploader in uploaders}
    
    async def upload_to_all(
        self,
        video: ProcessedVideo,
        platforms: Optional[List[Platform]] = None,
        skip_failed: bool = True
    ) -> Dict[Platform, Dict[str, Any]]:
        """Upload a video to all configured platforms."""
        
        if platforms is None:
            platforms = list(self.uploaders.keys())
        
        results = {}
        
        # Filter to only configured uploaders
        available_platforms = [
            p for p in platforms 
            if p in self.uploaders and self.uploaders[p].is_configured()
        ]
        
        if not available_platforms:
            print("No configured uploaders available")
            return results
        
        print(f"Uploading to {len(available_platforms)} platforms: {[p.value for p in available_platforms]}")
        
        # Upload to all platforms concurrently
        tasks = [
            self._upload_with_platform(video, platform)
            for platform in available_platforms
        ]
        
        platform_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for platform, result in zip(available_platforms, platform_results):
            if isinstance(result, Exception):
                results[platform] = {
                    "success": False,
                    "error": str(result),
                    "platform": platform.value
                }
                if not skip_failed:
                    raise result
            else:
                results[platform] = result
        
        # Update video status if all uploads succeeded
        successful_uploads = sum(1 for r in results.values() if r.get("success", False))
        if successful_uploads == len(results):
            video.status = VideoStatus.UPLOADED
        
        video.upload_results = results
        
        return results
    
    async def _upload_with_platform(
        self,
        video: ProcessedVideo,
        platform: Platform
    ) -> Dict[str, Any]:
        """Upload video to a specific platform with error handling."""
        
        uploader = self.uploaders[platform]
        
        try:
            # Authenticate if needed
            if not uploader.authenticated:
                auth_success = await uploader.authenticate()
                if not auth_success:
                    return {
                        "success": False,
                        "error": "Authentication failed",
                        "platform": platform.value
                    }
            
            # Perform upload
            result = await uploader.upload(video)
            
            if result.get("success"):
                print(f"✓ Successfully uploaded to {platform.value}")
            else:
                print(f"✗ Failed to upload to {platform.value}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            print(f"✗ Error uploading to {platform.value}: {e}")
            return {
                "success": False,
                "error": str(e),
                "platform": platform.value
            }
    
    async def batch_upload(
        self,
        videos: List[ProcessedVideo],
        platforms: Optional[List[Platform]] = None,
        concurrency_limit: int = 3
    ) -> List[Dict[Platform, Dict[str, Any]]]:
        """Upload multiple videos with controlled concurrency."""
        
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def upload_with_semaphore(video: ProcessedVideo) -> Dict[Platform, Dict[str, Any]]:
            async with semaphore:
                return await self.upload_to_all(video, platforms)
        
        tasks = [upload_with_semaphore(video) for video in videos]
        results = await asyncio.gather(*tasks)
        
        return list(results)
    
    def get_configured_platforms(self) -> List[Platform]:
        """Get list of platforms that are properly configured."""
        return [
            platform for platform, uploader in self.uploaders.items()
            if uploader.is_configured()
        ]
