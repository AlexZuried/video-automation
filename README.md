# Video Automation Pipeline

A robust, modular system for scraping viral videos from social media platforms, reviewing them with AI, and automatically uploading to multiple destinations.

## 🚀 Features

- **Multi-Platform Scraping**: Instagram Reels, TikTok, and Douyin
- **Engagement Filtering**: Filter by minimum likes (100k+) and views (1M+)
- **AI-Powered Review**: OpenAI GPT-4 analysis for quality and viral potential
- **Multi-Platform Upload**: Twitter/X, YouTube, Instagram, TikTok, Threads
- **Modular Architecture**: Easy to add new platforms or features
- **Async Processing**: Fast, concurrent operations
- **Comprehensive Logging**: Detailed logs with rotation
- **Configuration Management**: Environment-based configuration

## 📁 Project Structure

```
├── src/
│   ├── config/          # Configuration management
│   ├── scraper/         # Social media scrapers
│   │   ├── base.py      # Base scraper interface
│   │   ├── instagram.py # Instagram Reels scraper
│   │   ├── tiktok.py    # TikTok scraper
│   │   └── douyin.py    # Douyin scraper
│   ├── processor/       # Video processing & AI review
│   │   ├── ai_reviewer.py  # AI video analysis
│   │   └── pipeline.py     # Processing pipeline
│   ├── uploader/        # Social media uploaders
│   │   ├── base.py      # Base uploader interface
│   │   ├── twitter.py   # Twitter/X uploader
│   │   ├── youtube.py   # YouTube uploader
│   │   ├── instagram.py # Instagram uploader
│   │   ├── tiktok.py    # TikTok uploader
│   │   ├── threads.py   # Threads uploader
│   │   └── manager.py   # Upload manager
│   └── utils/           # Utilities & models
│       ├── logger.py    # Logging setup
│       └── models.py    # Data models
├── tests/               # Test suite
├── data/                # Data storage
│   ├── videos/          # Downloaded videos
│   ├── cache/           # Temporary cache
│   └── logs/            # Application logs
├── main.py              # Main entry point
└── requirements.txt     # Dependencies
```

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd <project-directory>
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

## ⚙️ Configuration

Edit `.env` file with your credentials:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Scraper Settings
MIN_LIKES=100000
MIN_VIEWS=1000000
MAX_VIDEOS_PER_RUN=50
HASHTAGS=viral,trending,fyp

# Social Media Credentials
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

YOUTUBE_API_KEY=...

INSTAGRAM_USERNAME=...
INSTAGRAM_PASSWORD=...

TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...

THREADS_ACCESS_TOKEN=...
```

## 🚀 Usage

### Basic Usage

Run the complete pipeline with default settings:

```bash
python main.py
```

### Custom Hashtags

```bash
python main.py --hashtags viral trending comedy dance
```

### Select Source Platforms

```bash
python main.py --source-platforms instagram tiktok douyin
```

### Select Upload Destinations

```bash
python main.py --upload-to twitter youtube instagram tiktok threads
```

### Adjust AI Review Threshold

```bash
python main.py --min-score 0.8
```

### Full Example

```bash
python main.py \
  --hashtags viral trending fyp comedy \
  --source-platforms instagram tiktok \
  --upload-to twitter youtube instagram \
  --min-score 0.75
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

With coverage report:

```bash
pytest tests/ -v --cov=src --cov-report=html
```

## 🔧 Adding New Platforms

### Adding a New Scraper

1. Create `src/scraper/newplatform.py`:

```python
from .base import BaseScraper
from ..utils.models import Platform, ScrapedVideoCollection

class NewPlatformScraper(BaseScraper):
    @property
    def platform(self) -> Platform:
        return Platform.NEWPLATFORM
    
    async def search_by_hashtag(self, hashtag: str, **kwargs):
        # Implement scraping logic
        pass
    
    async def get_video_metadata(self, video_url: str):
        # Implement metadata extraction
        pass
    
    async def download_video(self, video_url: str, save_path: str):
        # Implement video download
        pass
```

2. Register in `src/scraper/__init__.py`

### Adding a New Uploader

1. Create `src/uploader/newplatform.py`:

```python
from .base import BaseUploader
from ..utils.models import Platform

class NewPlatformUploader(BaseUploader):
    @property
    def platform(self) -> Platform:
        return Platform.NEWPLATFORM
    
    async def authenticate(self) -> bool:
        # Implement authentication
        pass
    
    async def upload(self, video):
        # Implement upload logic
        pass
    
    def is_configured(self) -> bool:
        # Check credentials
        pass
```

2. Register in `src/uploader/__init__.py`

## 📊 Workflow

1. **Scrape**: Search hashtags on source platforms
2. **Filter**: Apply engagement criteria (likes, views)
3. **Review**: AI analyzes content quality and viral potential
4. **Download**: Save approved videos locally
5. **Upload**: Distribute to destination platforms
6. **Log**: Track all operations and results

## ⚠️ Important Notes

- **API Limits**: Respect rate limits of all platforms
- **Terms of Service**: Ensure compliance with platform ToS
- **Authentication**: Some features require official API access
- **Video Rights**: Only use content you have rights to redistribute
- **Production Use**: Replace placeholder implementations with official APIs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

MIT License - See LICENSE file for details

## 🆘 Support

For issues and questions, please open an issue on GitHub.
