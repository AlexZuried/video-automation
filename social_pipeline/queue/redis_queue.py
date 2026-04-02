import aioredis
import json
import os
from loguru import logger

class RedisQueue:
    def __init__(self):
        self.redis = None
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))

    async def connect(self):
        try:
            self.redis = await aioredis.from_url(f"redis://{self.host}:{self.port}", db=0)
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

    async def push_task(self, task: dict):
        if self.redis:
            await self.redis.lpush("video_tasks", json.dumps(task))

    async def pop_task(self):
        if self.redis:
            data = await self.redis.brpop("video_tasks", timeout=5)
            if data:
                return json.loads(data[1])
        return None

    async def close(self):
        if self.redis:
            await self.redis.close()
