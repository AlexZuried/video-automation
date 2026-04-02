import asyncio
from typing import List, Dict
from loguru import logger
from ..processors.ai_scorer_http import AiScorerHttp
from ..queue.redis_queue import RedisQueue # Assumes you create this file next if needed

class MassUploadOrchestrator:
    def __init__(self):
        self.scorer = AiScorerHttp(threshold=6.0)
        # self.queue = RedisQueue() # Uncomment when redis_queue.py is added

    async def process_batch(self, videos: List[Dict]):
        logger.info(f"Starting batch processing for {len(videos)} videos...")
        
        tasks = [self._process_single(video) for video in videos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        accepted = sum(1 for r in results if isinstance(r, bool) and r)
        logger.info(f"Batch complete. Accepted: {accepted}, Rejected/Skipped: {len(videos)-accepted}")

    async def _process_single(self, video: Dict):
        url = video.get('url')
        metadata = video.get('metadata', {})
        
        # Step 1: AI Scoring
        is_accepted, score = await self.scorer.score_video(url, metadata)
        
        if not is_accepted:
            logger.warning(f"Video {url} rejected by AI (Score: {score}). Skipping upload.")
            return False
            
        # Step 2: Upload Logic (Placeholder)
        logger.info(f"Video {url} accepted. Proceeding to upload...")
        # await self.uploader.upload(video)
        
        return True

if __name__ == "__main__":
    # Test data
    videos = [
        {"url": "https://tiktok.com/@user/vid1", "metadata": {"likes": 150000, "views": 2000000}},
        {"url": "https://tiktok.com/@user/vid2", "metadata": {"likes": 500, "views": 1000}}
    ]
    orch = MassUploadOrchestrator()
    asyncio.run(orch.process_batch(videos))
