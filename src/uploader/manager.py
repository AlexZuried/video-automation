"""Multi-platform video uploader manager with retry logic."""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..utils.models import ProcessedVideo, Platform, VideoStatus
from ..utils.logger import get_logger
from .base import BaseUploader

logger = get_logger(__name__)


class UploadError(Exception):
    """Base exception for upload errors."""
    pass


class AuthenticationFailedError(UploadError):
    """Raised when authentication fails."""
    pass


class UploadManager:
    """Manages uploading videos to multiple social media platforms with retries."""
    
    def __init__(self, uploaders: List[BaseUploader], max_retries: int = 3, retry_delay: float = 2.0):
        self.uploaders = {uploader.platform: uploader for uploader in uploaders}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._upload_stats = {
            "total_attempts": 0,
            "successful_uploads": 0,
            "failed_uploads": 0
        }
    
    async def upload_to_all(
        self,
        video: ProcessedVideo,
        platforms: Optional[List[Platform]] = None,
        skip_failed: bool = True
    ) -> Dict[Platform, Dict[str, Any]]:
        """Upload a video to all configured platforms with retry logic."""
        
        if platforms is None:
            platforms = list(self.uploaders.keys())
        
        results = {}
        
        # Filter to only configured uploaders
        available_platforms = [
            p for p in platforms 
            if p in self.uploaders and self.uploaders[p].is_configured()
        ]
        
        if not available_platforms:
            logger.warning("No configured uploaders available")
            return results
        
        logger.info(f"Uploading to {len(available_platforms)} platforms: {[p.value for p in available_platforms]}")
        
        # Upload to all platforms concurrently
        tasks = [
            self._upload_with_retry(video, platform)
            for platform in available_platforms
        ]
        
        platform_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for platform, result in zip(available_platforms, platform_results):
            if isinstance(result, Exception):
                results[platform] = {
                    "success": False,
                    "error": str(result),
                    "platform": platform.value,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self._upload_stats["failed_uploads"] += 1
                if not skip_failed:
                    raise result
            else:
                results[platform] = result
                if result.get("success"):
                    self._upload_stats["successful_uploads"] += 1
                else:
                    self._upload_stats["failed_uploads"] += 1
        
        # Update video status if all uploads succeeded
        successful_uploads = sum(1 for r in results.values() if r.get("success", False))
        if successful_uploads == len(results) and len(results) > 0:
            video.status = VideoStatus.UPLOADED
        elif successful_uploads > 0:
            video.status = VideoStatus.PROCESSING  # Partially uploaded
        
        video.upload_results = results
        
        return results
    
    async def _upload_with_retry(
        self,
        video: ProcessedVideo,
        platform: Platform,
        force_auth: bool = False
    ) -> Dict[str, Any]:
        """Upload video to a specific platform with exponential backoff retry."""
        
        uploader = self.uploaders[platform]
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self._upload_stats["total_attempts"] += 1
                
                # Authenticate if needed
                if force_auth or not getattr(uploader, 'authenticated', True):
                    auth_success = await uploader.authenticate()
                    if not auth_success:
                        raise AuthenticationFailedError(f"Authentication failed for {platform.value}")
                
                # Perform upload
                result = await uploader.upload(video)
                
                if result.get("success"):
                    logger.success(f"✓ Successfully uploaded to {platform.value} (attempt {attempt + 1})")
                    result["attempts"] = attempt + 1
                    result["timestamp"] = datetime.utcnow().isoformat()
                    return result
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.warning(f"✗ Failed to upload to {platform.value}: {error_msg} (attempt {attempt + 1})")
                    
                    # Don't retry on authentication errors
                    if 'auth' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                        raise AuthenticationFailedError(error_msg)
                    
                    last_error = error_msg
                    
            except AuthenticationFailedError as e:
                logger.error(f"Authentication failed for {platform.value}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "platform": platform.value,
                    "attempts": attempt + 1,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error uploading to {platform.value} (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        logger.error(f"All {self.max_retries} attempts failed for {platform.value}: {last_error}")
        return {
            "success": False,
            "error": f"All retries failed: {last_error}",
            "platform": platform.value,
            "attempts": self.max_retries,
            "timestamp": datetime.utcnow().isoformat()
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
        
        logger.info(f"Batch upload complete: {len(videos)} videos processed")
        logger.info(f"Stats: {self._upload_stats}")
        
        return list(results)
    
    def get_configured_platforms(self) -> List[Platform]:
        """Get list of platforms that are properly configured."""
        return [
            platform for platform, uploader in self.uploaders.items()
            if uploader.is_configured()
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get upload statistics."""
        stats = self._upload_stats.copy()
        stats["success_rate"] = (
            stats["successful_uploads"] / stats["total_attempts"] 
            if stats["total_attempts"] > 0 else 0
        )
        stats["configured_platforms"] = [p.value for p in self.get_configured_platforms()]
        return stats
    
    async def health_check(self) -> Dict[Platform, bool]:
        """Check health/status of all configured platforms."""
        health_status = {}
        
        for platform, uploader in self.uploaders.items():
            try:
                if not uploader.is_configured():
                    health_status[platform] = False
                    continue
                
                # Try to authenticate (without actually uploading)
                is_authenticated = await uploader.authenticate()
                health_status[platform] = is_authenticated
                
            except Exception as e:
                logger.warning(f"Health check failed for {platform.value}: {e}")
                health_status[platform] = False
        
        return health_status
