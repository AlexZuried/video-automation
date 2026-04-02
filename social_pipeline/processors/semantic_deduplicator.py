import hashlib
from typing import List, Dict, Set
from loguru import logger
# Note: Requires 'imagehash' and 'Pillow' installed

class SemanticDeduplicator:
    def __init__(self):
        self.seen_hashes: Set[str] = set()

    def is_duplicate(self, video_data: bytes) -> bool:
        # In a real scenario, extract a frame and compute pHash
        # Here we simulate with content hash
        h = hashlib.md5(video_data).hexdigest()
        if h in self.seen_hashes:
            logger.warning(f"Duplicate detected: {h}")
            return True
        self.seen_hashes.add(h)
        return False

    def check_metadata_similarity(self, meta: Dict, threshold: float = 0.85) -> bool:
        # Simulate checking if caption/hashtags are too similar to previous
        sig = f"{meta.get('description', '')}{sorted(meta.get('hashtags', []))}"
        h = hashlib.sha1(sig.encode()).hexdigest()[:10]
        if h in self.seen_hashes:
            return True
        self.seen_hashes.add(h)
        return False
