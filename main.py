import asyncio
import yaml
import os
from dotenv import load_dotenv
from loguru import logger
from src.scraper import TikTokScraper, InstagramScraper
from social_pipeline.orchestrator import MassUploadOrchestrator

load_dotenv()

async def main():
    # Load Config
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)

    logger.add(config['logging']['file'], rotation="500 MB")
    logger.info("🚀 Video Automation Pipeline Started")

    # Initialize Components
    tiktok_scraper = TikTokScraper()
    ig_scraper = InstagramScraper()
    orchestrator = MassUploadOrchestrator()

    try:
        # 1. Scrape
        hashtags = ["viral", "trending"]
        all_videos = []
        
        for tag in hashtags:
            tt_videos = await tiktok_scraper.scrape_hashtag(tag, limit=5)
            ig_videos = await ig_scraper.scrape_hashtag(tag, limit=5)
            all_videos.extend(tt_videos + ig_videos)

        logger.info(f"Found {len(all_videos)} videos to process")

        # 2. Process & Upload
        await orchestrator.process_batch(all_videos)

    finally:
        await tiktok_scraper.close()
        await ig_scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
