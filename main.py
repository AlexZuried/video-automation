#!/usr/bin/env python3
"""
Main entry point for the video automation pipeline.

This script orchestrates the complete workflow:
1. Scrape videos from Instagram, TikTok, and Douyin based on hashtags
2. Filter by engagement criteria (likes, views)
3. Send to AI for review and approval
4. Download approved videos
5. Upload to multiple social media platforms
"""
import asyncio
import argparse
from pathlib import Path
from loguru import logger

from src.config import load_config
from src.utils import setup_logger, Platform
from src.scraper import InstagramScraper, TikTokScraper, DouyinScraper, get_scraper
from src.processor import VideoReviewer, VideoProcessor
from src.uploader import (
    TwitterUploader, 
    YouTubeUploader, 
    InstagramUploader,
    TikTokUploader,
    ThreadsUploader,
    UploadManager
)


async def run_pipeline(
    hashtags: list,
    platforms: list,
    upload_to: list,
    min_score: float = 0.7
):
    """Execute the complete video automation pipeline."""
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    setup_logger(config.log_file)
    logger.info("Starting video automation pipeline")
    logger.info(f"Hashtags: {hashtags}")
    logger.info(f"Source platforms: {platforms}")
    logger.info(f"Upload destinations: {upload_to}")
    
    # Step 1: Scrape videos from source platforms
    logger.info("=" * 50)
    logger.info("STEP 1: Scraping videos from social media")
    logger.info("=" * 50)
    
    all_videos = []
    
    for platform_name in platforms:
        try:
            scraper = get_scraper(platform_name)
            logger.info(f"Scraping {platform_name}...")
            
            async with scraper:
                for hashtag in hashtags:
                    logger.info(f"  Searching hashtag: #{hashtag}")
                    
                    collection = await scraper.search_by_hashtag(
                        hashtag=hashtag,
                        min_likes=config.scraper.min_likes,
                        min_views=config.scraper.min_views,
                        max_results=config.scraper.max_videos_per_run
                    )
                    
                    logger.info(f"  Found {collection.total_count} videos, {collection.filtered_count} matching criteria")
                    all_videos.extend(collection.videos)
        
        except Exception as e:
            logger.error(f"Error scraping {platform_name}: {e}")
            continue
    
    if not all_videos:
        logger.warning("No videos found matching criteria. Exiting.")
        return
    
    logger.info(f"Total videos collected: {len(all_videos)}")
    
    # Step 2: AI Review
    logger.info("=" * 50)
    logger.info("STEP 2: AI Review and Analysis")
    logger.info("=" * 50)
    
    if not config.ai.api_key:
        logger.error("OpenAI API key not configured. Cannot perform AI review.")
        return
    
    reviewer = VideoReviewer(
        api_key=config.ai.api_key,
        model=config.ai.model
    )
    
    processor = VideoProcessor(
        reviewer=reviewer,
        cache_dir=config.video_cache_dir,
        output_dir=config.video_output_dir
    )
    
    processed_videos = await processor.process_videos(
        videos=all_videos,
        review_criteria=config.ai.review_criteria,
        min_score=min_score,
        download_videos=True
    )
    
    logger.info(f"Videos approved and downloaded: {len(processed_videos)}")
    
    if not processed_videos:
        logger.warning("No videos approved after AI review. Exiting.")
        return
    
    # Save results to file
    await processor.save_results_to_file(
        processed_videos,
        "data/videos/approved_videos.json"
    )
    
    # Step 3: Upload to destination platforms
    logger.info("=" * 50)
    logger.info("STEP 3: Uploading to social media platforms")
    logger.info("=" * 50)
    
    # Create uploaders for requested platforms
    uploaders = []
    sm_config = config.social_media
    
    platform_uploaders = {
        "twitter": lambda: TwitterUploader(
            api_key=sm_config.twitter_api_key,
            api_secret=sm_config.twitter_api_secret,
            access_token=sm_config.twitter_access_token,
            access_token_secret=sm_config.twitter_access_token_secret
        ),
        "youtube": lambda: YouTubeUploader(api_key=sm_config.youtube_api_key),
        "instagram": lambda: InstagramUploader(
            username=sm_config.instagram_username,
            password=sm_config.instagram_password
        ),
        "tiktok": lambda: TikTokUploader(
            client_key=sm_config.tiktok_client_key,
            client_secret=sm_config.tiktok_client_secret
        ),
        "threads": lambda: ThreadsUploader(access_token=sm_config.threads_access_token)
    }
    
    for platform_name in upload_to:
        if platform_name in platform_uploaders:
            uploader = platform_uploaders[platform_name]()
            if uploader.is_configured():
                uploaders.append(uploader)
                logger.info(f"✓ {platform_name} uploader configured")
            else:
                logger.warning(f"✗ {platform_name} uploader not configured (missing credentials)")
        else:
            logger.warning(f"Unknown platform: {platform_name}")
    
    if not uploaders:
        logger.error("No uploaders configured. Skipping upload step.")
        return
    
    # Create upload manager and upload videos
    upload_manager = UploadManager(uploaders)
    
    configured_platforms = upload_manager.get_configured_platforms()
    logger.info(f"Uploading {len(processed_videos)} videos to {len(configured_platforms)} platforms")
    
    for i, video in enumerate(processed_videos, 1):
        logger.info(f"\nUploading video {i}/{len(processed_videos)}: {video.metadata.title}")
        
        results = await upload_manager.upload_to_all(
            video=video,
            platforms=configured_platforms
        )
        
        # Log results
        for platform, result in results.items():
            if result.get("success"):
                logger.success(f"  ✓ {platform.value}: {result.get('url', 'Uploaded')}")
            else:
                logger.error(f"  ✗ {platform.value}: {result.get('error', 'Failed')}")
    
    logger.info("=" * 50)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 50)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Video Automation Pipeline - Scrape, Review, and Upload videos"
    )
    
    parser.add_argument(
        "--hashtags", "-t",
        nargs="+",
        default=["viral", "trending", "fyp"],
        help="Hashtags to search for (default: viral trending fyp)"
    )
    
    parser.add_argument(
        "--source-platforms", "-s",
        nargs="+",
        choices=["instagram", "tiktok", "douyin"],
        default=["instagram", "tiktok"],
        help="Source platforms to scrape from (default: instagram tiktok)"
    )
    
    parser.add_argument(
        "--upload-to", "-u",
        nargs="+",
        choices=["twitter", "youtube", "instagram", "tiktok", "threads"],
        default=["twitter", "youtube"],
        help="Destination platforms to upload to (default: twitter youtube)"
    )
    
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="Minimum AI review score for approval (default: 0.7)"
    )
    
    args = parser.parse_args()
    
    # Run the async pipeline
    asyncio.run(run_pipeline(
        hashtags=args.hashtags,
        platforms=args.source_platforms,
        upload_to=args.upload_to,
        min_score=args.min_score
    ))


if __name__ == "__main__":
    main()
