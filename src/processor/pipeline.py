"""Video processing pipeline."""
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..utils.models import (
    VideoMetadata, 
    ProcessedVideo, 
    VideoStatus,
    AIReviewResult,
    Platform
)
from .ai_reviewer import VideoReviewer


class VideoProcessor:
    """Main video processing pipeline orchestrator."""
    
    def __init__(
        self,
        reviewer: VideoReviewer,
        cache_dir: str = "data/cache",
        output_dir: str = "data/videos"
    ):
        self.reviewer = reviewer
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_videos(
        self,
        videos: List[VideoMetadata],
        review_criteria: List[str],
        min_score: float = 0.7,
        download_videos: bool = True
    ) -> List[ProcessedVideo]:
        """Process a batch of videos through the complete pipeline."""
        
        processed_videos = []
        
        # Step 1: AI Review all videos
        print(f"Starting AI review for {len(videos)} videos...")
        reviews = await self.reviewer.batch_review(videos, review_criteria)
        
        # Create review lookup
        review_map = {r.video_id: r for r in reviews}
        
        # Step 2: Filter by approval and score
        approved_videos = []
        for video in videos:
            review = review_map.get(video.video_id)
            
            if review and review.is_approved and review.score >= min_score:
                approved_videos.append((video, review))
                print(f"✓ Video {video.video_id} approved (score: {review.score:.2f})")
            else:
                print(f"✗ Video {video.video_id} rejected")
        
        print(f"Approved {len(approved_videos)}/{len(videos)} videos")
        
        # Step 3: Download approved videos
        if download_videos:
            print(f"Downloading {len(approved_videos)} approved videos...")
            for video, review in approved_videos:
                processed = await self._download_and_process_video(video, review)
                if processed:
                    processed_videos.append(processed)
        else:
            # Create processed video entries without downloading
            for video, review in approved_videos:
                processed = ProcessedVideo(
                    metadata=video,
                    local_path="",
                    ai_review=review,
                    status=VideoStatus.REVIEWED
                )
                processed_videos.append(processed)
        
        return processed_videos
    
    async def _download_and_process_video(
        self,
        video: VideoMetadata,
        review: AIReviewResult
    ) -> Optional[ProcessedVideo]:
        """Download and process a single video."""
        
        from ..scraper import get_scraper
        
        try:
            # Get appropriate scraper for the platform
            scraper = get_scraper(video.platform.value)
            
            # Generate filename
            filename = f"{video.platform.value}_{video.video_id}.mp4"
            save_path = self.output_dir / filename
            
            async with scraper:
                success = await scraper.download_video(video.url, str(save_path))
                
                if not success:
                    print(f"Failed to download video {video.video_id}")
                    return None
                
                # Update status
                processed_video = ProcessedVideo(
                    metadata=video,
                    local_path=str(save_path),
                    ai_review=review,
                    status=VideoStatus.APPROVED
                )
                
                # Save metadata to file
                await self._save_metadata(processed_video)
                
                return processed_video
                
        except Exception as e:
            print(f"Error processing video {video.video_id}: {e}")
            return None
    
    async def _save_metadata(self, processed_video: ProcessedVideo) -> None:
        """Save video metadata to JSON file."""
        
        metadata_file = self.output_dir / f"{Path(processed_video.local_path).stem}_metadata.json"
        
        metadata_dict = {
            "metadata": processed_video.metadata.model_dump(mode='json', default=str),
            "ai_review": processed_video.ai_review.model_dump(mode='json', default=str) if processed_video.ai_review else None,
            "status": processed_video.status.value,
            "local_path": processed_video.local_path,
            "processed_at": processed_video.processed_at.isoformat()
        }
        
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(str(metadata_dict))
    
    async def save_results_to_file(
        self,
        processed_videos: List[ProcessedVideo],
        output_file: str = "data/videos/approved_videos.json"
    ) -> None:
        """Save all processed video results to a single JSON file."""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results = [
            {
                "metadata": pv.metadata.model_dump(mode='json', default=str),
                "ai_review": pv.ai_review.model_dump(mode='json', default=str) if pv.ai_review else None,
                "status": pv.status.value,
                "local_path": pv.local_path,
                "processed_at": pv.processed_at.isoformat()
            }
            for pv in processed_videos
        ]
        
        async with aiofiles.open(output_path, 'w') as f:
            import json
            await f.write(json.dumps(results, indent=2, default=str))
        
        print(f"Saved {len(results)} video results to {output_file}")
