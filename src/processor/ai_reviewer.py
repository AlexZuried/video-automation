"""AI video review and analysis module."""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from openai import AsyncOpenAI
from ..utils.models import VideoMetadata, AIReviewResult


class VideoReviewer:
    """AI-powered video content reviewer."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def review_video(
        self,
        metadata: VideoMetadata,
        criteria: List[str],
        max_retries: int = 3
    ) -> Optional[AIReviewResult]:
        """Review video content using AI."""
        
        prompt = self._build_review_prompt(metadata, criteria)
        
        for attempt in range(max_retries):
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
                
                result_data = json.loads(response.choices[0].message.content)
                
                return AIReviewResult(
                    video_id=metadata.video_id,
                    is_approved=result_data.get("is_approved", False),
                    score=float(result_data.get("score", 0.5)),
                    reasons=result_data.get("reasons", []),
                    suggestions=result_data.get("suggestions", []),
                    categories=result_data.get("categories", []),
                    viral_potential=result_data.get("viral_potential", "unknown"),
                    raw_response=result_data
                )
                
            except Exception as e:
                print(f"AI review attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    print(f"All {max_retries} attempts failed for video {metadata.video_id}")
                    return None
        
        return None
    
    def _build_review_prompt(self, metadata: VideoMetadata, criteria: List[str]) -> str:
        """Build the review prompt for AI."""
        
        criteria_str = ", ".join(criteria)
        
        prompt = f"""
Analyze this video content for viral potential and quality based on these criteria: {criteria_str}

Video Metadata:
- Platform: {metadata.platform.value}
- Title: {metadata.title}
- Description: {metadata.description[:200]}
- Author: {metadata.author}
- Engagement:
  * Likes: {metadata.likes:,}
  * Views: {metadata.views:,}
  * Comments: {metadata.comments:,}
  * Shares: {metadata.shares:,}
- Hashtags: {', '.join(metadata.hashtags)}
- Duration: {metadata.duration or 'Unknown'} seconds

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
2. Engagement rate (likes/views ratio)
3. Trending potential
4. Brand safety
5. Audience appeal
6. Originality
"""
        
        return prompt
    
    async def batch_review(
        self,
        videos: List[VideoMetadata],
        criteria: List[str],
        concurrency_limit: int = 5
    ) -> List[AIReviewResult]:
        """Review multiple videos with controlled concurrency."""
        import asyncio
        
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def review_with_semaphore(video: VideoMetadata) -> Optional[AIReviewResult]:
            async with semaphore:
                return await self.review_video(video, criteria)
        
        tasks = [review_with_semaphore(video) for video in videos]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        return [r for r in results if r is not None]
