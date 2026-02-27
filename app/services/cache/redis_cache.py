# app/services/cache/redis_cache.py
import redis.asyncio as aioredis
import orjson
from typing import Any
from datetime import timedelta

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    _pool: aioredis.Redis | None = None
    _available: bool = False

    @classmethod
    async def initialize(cls) -> None:
        """Подключиться к Redis. Если недоступен — работаем без кэша."""
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not set, running without cache")
            return

        try:
            cls._pool = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            await cls._pool.ping()
            cls._available = True
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Running without cache.")
            cls._pool = None
            cls._available = False

    @classmethod
    async def close(cls) -> None:
        if cls._pool:
            try:
                await cls._pool.close()
            except Exception:
                pass

    @classmethod
    def is_available(cls) -> bool:
        return cls._available and cls._pool is not None

    @classmethod
    async def get(cls, key: str) -> Any | None:
        if not cls.is_available():
            return None
        try:
            raw = await cls._pool.get(key)
            if raw:
                return orjson.loads(raw)
        except Exception as e:
            logger.debug(f"Redis GET error: {e}")
        return None

    @classmethod
    async def set(
        cls, key: str, value: Any, ttl: int | timedelta = 300
    ) -> None:
        if not cls.is_available():
            return
        try:
            data = orjson.dumps(value)
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            await cls._pool.set(key, data, ex=ttl)
        except Exception as e:
            logger.debug(f"Redis SET error: {e}")

    @classmethod
    async def delete(cls, key: str) -> None:
        if not cls.is_available():
            return
        try:
            await cls._pool.delete(key)
        except Exception as e:
            logger.debug(f"Redis DELETE error: {e}")

    @classmethod
    async def increment(cls, key: str, ttl: int = 86400) -> int:
        if not cls.is_available():
            return 1
        try:
            pipe = cls._pool.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.debug(f"Redis INCR error: {e}")
            return 1

    @classmethod
    async def get_rate_limit(
        cls, user_id: int, action: str, limit: int, window: int
    ) -> bool:
        """True если лимит НЕ превышен. Без Redis — всегда разрешаем."""
        if not cls.is_available():
            return True
        try:
            key = f"rate:{action}:{user_id}"
            current = await cls.increment(key, window)
            return current <= limit
        except Exception:
            return True

    @classmethod
    async def publish(cls, channel: str, message: dict) -> None:
        if not cls.is_available():
            return
        try:
            await cls._pool.publish(channel, orjson.dumps(message))
        except Exception as e:
            logger.debug(f"Redis PUBLISH error: {e}")

    @classmethod
    async def enqueue_task(cls, queue: str, task_data: dict) -> None:
        if not cls.is_available():
            return
        try:
            await cls._pool.rpush(f"queue:{queue}", orjson.dumps(task_data))
        except Exception as e:
            logger.debug(f"Redis ENQUEUE error: {e}")

    @classmethod
    async def dequeue_task(cls, queue: str, timeout: int = 5) -> dict | None:
        if not cls.is_available():
            return None
        try:
            result = await cls._pool.blpop(f"queue:{queue}", timeout=timeout)
            if result:
                return orjson.loads(result[1])
        except Exception as e:
            logger.debug(f"Redis DEQUEUE error: {e}")
        return None

    @classmethod
    def get_pool(cls) -> aioredis.Redis | None:
        return cls._pool if cls.is_available() else None
