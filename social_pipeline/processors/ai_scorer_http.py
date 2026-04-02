import httpx
import re
import asyncio
from typing import Optional, Tuple, Dict
from loguru import logger

class AiScorerHttp:
    """
    Lightweight AI Scorer using free HTTP endpoints or Heuristic Fallback.
    No API Key required. No Browser automation.
    """
    
    def __init__(self, threshold: float = 6.0):
        self.threshold = threshold
        self.client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self.client.aclose()

    async def score_video(self, video_url: str, metadata: dict) -> Tuple[bool, float]:
        """
        Returns (is_accepted, score)
        """
        prompt = self._build_prompt(video_url, metadata)
        score = None
        
        try:
            # Attempt to call a free inference API (Placeholder for real endpoint)
            # Since truly free unauthenticated LLM APIs are unstable, we simulate
            # the request structure and fall back to heuristics if it fails.
            score = await self._call_ai_api(prompt)
            
            if score is None:
                logger.warning("AI API unavailable. Using heuristic fallback.")
                score = self._heuristic_fallback(metadata)
                
        except Exception as e:
            logger.error(f"AI Scoring error: {e}. Using heuristic fallback.")
            score = self._heuristic_fallback(metadata)

        is_accepted = score > self.threshold
        status = "✅ ACCEPTED" if is_accepted else "❌ REJECTED"
        
        logger.info(f"[AI SCORER] URL: {video_url[:50]}... | Score: {score:.1f} | Status: {status}")
        
        return is_accepted, score

    def _build_prompt(self, url: str, meta: dict) -> str:
        return f"""
        Analyze this video potential based on metadata:
        URL: {url}
        Caption: {meta.get('description', 'N/A')}
        Hashtags: {', '.join(meta.get('hashtags', []))}
        Stats: {meta.get('likes', 0)} likes, {meta.get('views', 0)} views.
        
        Task: Rate viral potential from 1 to 10. Return ONLY the number.
        """

    async def _call_ai_api(self, prompt: str) -> Optional[float]:
        """
        Placeholder for actual API call. 
        Returns None to trigger fallback in this demo environment.
        """
        # Example: response = await self.client.post("https://api.free-llm.com...", json={"prompt": prompt})
        # Parse response for number using regex r'\b([1-9]|10)\b'
        return None 

    def _heuristic_fallback(self, meta: dict) -> float:
        """
        Smart scoring based on metrics if AI is unavailable.
        Formula: Log-based scoring on likes/views ratio.
        """
        likes = meta.get('likes', 0)
        views = meta.get('views', 1)
        
        if views == 0: return 1.0
        
        engagement_rate = (likes / views) * 100
        score = 5.0 # Base score
        
        if engagement_rate > 10: score += 4.0
        elif engagement_rate > 5: score += 3.0
        elif engagement_rate > 2: score += 2.0
        
        if likes > 100000: score += 1.0
        if views > 1000000: score += 1.0
        
        return min(score, 10.0)
