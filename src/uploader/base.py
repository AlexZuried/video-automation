"""Base uploader interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from ..utils.models import ProcessedVideo, Platform


class BaseUploader(ABC):
    """Abstract base class for social media uploaders."""
    
    @abstractmethod
    async def upload(self, video: ProcessedVideo) -> Dict[str, Any]:
        """Upload a processed video to the platform."""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform API."""
        pass
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform this uploader handles."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the uploader is properly configured with credentials."""
        pass
