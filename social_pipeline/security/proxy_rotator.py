import random
from typing import List, Optional
from loguru import logger

class ProxyRotator:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.current_index = 0

    def get_next_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = random.choice(self.proxies)
        logger.debug(f"Rotated proxy: {proxy}")
        return proxy
