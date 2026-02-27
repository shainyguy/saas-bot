# app/services/cache/redis_cache.py
import redis.asyncio as aioredis
import orjson
from typing import Any, Optional
from datetime import timedelta

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    _pool: aioredis.Redis | None = None

    @classmethod
    async def initialize(cls) -> None:
        cls._pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,
            max_connections=20,
        )
        await cls._pool.ping()
        logger.info("Redis connected")

    @classmethod
    async def close(cls) -> None:
        if cls._pool:
            await cls._pool.close()

    @classmethod
    async def get(cls, key: str) -> Any | None:
        raw = await cls._pool.get(key)
        if raw:
            return orjson.loads(raw)
        return None

    @classmethod
    async def set(
        cls, key: str, value: Any, ttl: int | timedelta = 300
    ) -> None:
        data = orjson.dumps(value)
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())
        await cls._pool.set(key, data, ex=ttl)

    @classmethod
    async def delete(cls, key: str) -> None:
        await cls._pool.delete(key)

    @classmethod
    async def increment(cls, key: str, ttl: int = 86400) -> int:
        pipe = cls._pool.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        return results[0]

    @classmethod
    async def get_rate_limit(cls, user_id: int, action: str, limit: int, window: int) -> bool:
        """True если лимит НЕ превышен."""
        key = f"rate:{action}:{user_id}"
        current = await cls.increment(key, window)
        return current <= limit

    @classmethod
    async def publish(cls, channel: str, message: dict) -> None:
        await cls._pool.publish(channel, orjson.dumps(message))

    @classmethod
    async def enqueue_task(cls, queue: str, task_data: dict) -> None:
        await cls._pool.rpush(f"queue:{queue}", orjson.dumps(task_data))

    @classmethod
    async def dequeue_task(cls, queue: str, timeout: int = 5) -> dict | None:
        result = await cls._pool.blpop(f"queue:{queue}", timeout=timeout)
        if result:
            return orjson.loads(result[1])
        return None

    @classmethod
    def get_pool(cls) -> aioredis.Redis:
        if not cls._pool:
            raise RuntimeError("Redis not initialized")
        return cls._pool