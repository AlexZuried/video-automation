import asyncio
from typing import List, Dict
from loguru import logger
from ..processors.ai_scorer_http import AiScorerHttp

class MassUploadOrchestrator:
    def __init__(self):
        self.scorer = AiScorerHttp(threshold=6.0)

    async def process_batch(self, videos: List[Dict]):
        logger.info(f"🚀 Starting batch processing for {len(videos)} videos...")
        
        tasks = [self._process_single(video) for video in videos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        accepted = sum(1 for r in results if isinstance(r, bool) and r)
        logger.info(f"✅ Batch complete. Accepted: {accepted}, Rejected/Skipped: {len(videos)-accepted}")

    async def _process_single(self, video: Dict):
        url = video.get('url')
        metadata = video.get('metadata', {})
        
        # Step 1: AI Scoring
        logger.info(f"🧠 Analyzing: {url}")
        is_accepted, score = await self.scorer.score_video(url, metadata)
        
        if not is_accepted:
            logger.warning(f"⛔ Video {url} rejected by AI (Score: {score}). Skipping upload.")
            return False
            
        # Step 2: Upload Logic (Placeholder)
        logger.info(f"⬆️ Video {url} accepted. Proceeding to upload...")
        # await self.uploader.upload(video)
        
        return True
