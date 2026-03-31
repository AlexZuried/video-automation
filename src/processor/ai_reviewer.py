"""AI video review and analysis module."""
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import aiofiles
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from ..utils.models import VideoMetadata, AIReviewResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ReviewCache:
    """Cache for AI review results to avoid redundant API calls."""
    
    def __init__(self, cache_dir: str = "data/cache/reviews"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, metadata: VideoMetadata) -> str:
        """Generate a unique cache key for video metadata."""
        content = f"{metadata.video_id}:{metadata.platform.value}:{metadata.likes}:{metadata.views}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get(self, metadata: VideoMetadata) -> Optional[AIReviewResult]:
        """Get cached review result if available."""
        cache_key = self._get_cache_key(metadata)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    data = json.loads(await f.read())
                    logger.debug(f"Cache hit for video {metadata.video_id}")
                    return AIReviewResult(**data)
            except Exception as e:
                logger.warning(f"Error reading cache for {metadata.video_id}: {e}")
        
        return None
    
    async def set(self, metadata: VideoMetadata, result: AIReviewResult) -> None:
        """Cache a review result."""
        cache_key = self._get_cache_key(metadata)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(result.model_dump_json())
            logger.debug(f"Cached review for video {metadata.video_id}")
        except Exception as e:
            logger.warning(f"Error caching review for {metadata.video_id}: {e}")


class VideoReviewer:
    """AI-powered video content reviewer with caching and retry logic."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4-turbo-preview",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_cache: bool = True,
        cache_dir: str = "data/cache/reviews"
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_cache = use_cache
        self.cache = ReviewCache(cache_dir) if use_cache else None
        self._request_count = 0
        self._cache_hits = 0
    
    async def review_video(
        self,
        metadata: VideoMetadata,
        criteria: List[str],
        force_refresh: bool = False
    ) -> Optional[AIReviewResult]:
        """Review video content using AI with caching and exponential backoff."""
        
        # Check cache first
        if not force_refresh and self.cache:
            cached_result = await self.cache.get(metadata)
            if cached_result:
                self._cache_hits += 1
                return cached_result
        
        prompt = self._build_review_prompt(metadata, criteria)
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert video content analyst. Review videos for quality, engagement potential, and viral characteristics. Provide structured JSON responses."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                self._request_count += 1
                result_data = json.loads(response.choices[0].message.content)
                
                result = AIReviewResult(
                    video_id=metadata.video_id,
                    is_approved=result_data.get("is_approved", False),
                    score=float(result_data.get("score", 0.5)),
                    reasons=result_data.get("reasons", []),
                    suggestions=result_data.get("suggestions", []),
                    categories=result_data.get("categories", []),
                    viral_potential=result_data.get("viral_potential", "unknown"),
                    raw_response=result_data
                )
                
                # Cache the result
                if self.cache:
                    await self.cache.set(metadata, result)
                
                logger.info(f"Reviewed video {metadata.video_id}: score={result.score:.2f}, approved={result.is_approved}")
                return result
                
            except RateLimitError as e:
                last_error = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(wait_time)
                
            except APITimeoutError as e:
                last_error = e
                logger.warning(f"API timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    
            except APIError as e:
                last_error = e
                logger.error(f"API error: {e}")
                break  # Don't retry on API errors
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.error(f"Failed to parse AI response as JSON: {e}")
                break  # Don't retry on parsing errors
                
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error reviewing video {metadata.video_id}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        
        logger.error(f"All {self.max_retries} attempts failed for video {metadata.video_id}: {last_error}")
        return None
    
    def _build_review_prompt(self, metadata: VideoMetadata, criteria: List[str]) -> str:
        """Build the review prompt for AI."""
        
        criteria_str = ", ".join(criteria)
        engagement_rate = (metadata.likes / metadata.views * 100) if metadata.views > 0 else 0
        
        prompt = f"""
Analyze this video content for viral potential and quality based on these criteria: {criteria_str}

Video Metadata:
- Platform: {metadata.platform.value}
- Video ID: {metadata.video_id}
- Title: {metadata.title}
- Description: {metadata.description[:200]}
- Author: {metadata.author}
- Engagement Metrics:
  * Likes: {metadata.likes:,}
  * Views: {metadata.views:,}
  * Comments: {metadata.comments:,}
  * Shares: {metadata.shares:,}
  * Engagement Rate: {engagement_rate:.2f}%
- Hashtags: {', '.join(metadata.hashtags)}
- Duration: {metadata.duration or 'Unknown'} seconds
- Created: {metadata.created_at.isoformat() if metadata.created_at else 'Unknown'}

Provide your analysis in JSON format with these fields:
{{
    "is_approved": boolean,
    "score": number (0.0 to 1.0),
    "reasons": ["array of reasons for approval/rejection"],
    "suggestions": ["array of improvement suggestions"],
    "categories": ["array of content categories"],
    "viral_potential": "low|medium|high"
}}

Consider:
1. Content quality and production value
2. Engagement rate (likes/views ratio) - higher is better
3. Trending potential based on hashtags and timing
4. Brand safety and content guidelines
5. Audience appeal and demographic fit
6. Originality and creativity
7. Cross-platform suitability
8. Compliance with platform-specific rules

Be critical but fair. Only approve videos with genuine viral potential.
"""
        
        return prompt
    
    async def batch_review(
        self,
        videos: List[VideoMetadata],
        criteria: List[str],
        concurrency_limit: int = 5,
        force_refresh: bool = False
    ) -> List[AIReviewResult]:
        """Review multiple videos with controlled concurrency."""
        
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def review_with_semaphore(video: VideoMetadata) -> Optional[AIReviewResult]:
            async with semaphore:
                return await self.review_video(video, criteria, force_refresh)
        
        tasks = [review_with_semaphore(video) for video in videos]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        valid_results = [r for r in results if r is not None]
        
        logger.info(f"Batch review complete: {len(valid_results)}/{len(videos)} videos reviewed successfully")
        if self.cache:
            logger.info(f"Cache stats: {self._cache_hits} hits, {self._request_count} API calls")
        
        return valid_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reviewer statistics."""
        return {
            "total_requests": self._request_count,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / (self._request_count + self._cache_hits) if (self._request_count + self._cache_hits) > 0 else 0,
            "model": self.model,
            "cache_enabled": self.use_cache
        }
