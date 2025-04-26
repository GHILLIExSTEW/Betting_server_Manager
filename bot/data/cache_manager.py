import aioredis
import json
import logging
from typing import Optional, Any, Dict, List
from bot.utils.errors import DatabaseConnectionError
from bot.config.settings import (
    CACHE_HOST,
    CACHE_PORT,
    CACHE_PASSWORD
)

logger = logging.getLogger(__name__)

class CacheManager:
    _redis = None

    @classmethod
    async def get_redis(cls):
        """Get or create Redis connection"""
        if cls._redis is None:
            try:
                cls._redis = await aioredis.from_url(
                    f"redis://{CACHE_HOST}:{CACHE_PORT}",
                    password=CACHE_PASSWORD,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._redis

    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._redis:
            await cls._redis.close()
            cls._redis = None
            logger.info("Redis connection closed")

    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            redis = await cls.get_redis()
            return await redis.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    @classmethod
    async def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        try:
            redis = await cls.get_redis()
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await redis.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete value from cache"""
        try:
            redis = await cls.get_redis()
            await redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    @classmethod
    async def get_json(cls, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        try:
            value = await cls.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get_json error: {e}")
            return None

    @classmethod
    async def set_json(cls, key: str, value: Dict, ttl: Optional[int] = None) -> bool:
        """Set JSON value in cache"""
        try:
            return await cls.set(key, json.dumps(value), ttl)
        except Exception as e:
            logger.error(f"Cache set_json error: {e}")
            return False

    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            redis = await cls.get_redis()
            return await redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    @classmethod
    async def increment(cls, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in cache"""
        try:
            redis = await cls.get_redis()
            return await redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None

    @classmethod
    async def decrement(cls, key: str, amount: int = 1) -> Optional[int]:
        """Decrement value in cache"""
        try:
            redis = await cls.get_redis()
            return await redis.decrby(key, amount)
        except Exception as e:
            logger.error(f"Cache decrement error: {e}")
            return None

    async def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """Add elements to a sorted set"""
        try:
            redis = await self.get_redis()
            return await redis.zadd(name, mapping)
        except Exception as e:
            logger.error(f"Error adding to sorted set {name}: {e}")
            return 0

    async def zrange(self, name: str, start: int, end: int, withscores: bool = False) -> List[Any]:
        """Get a range from a sorted set"""
        try:
            redis = await self.get_redis()
            return await redis.zrange(name, start, end, withscores=withscores)
        except Exception as e:
            logger.error(f"Error getting range from sorted set {name}: {e}")
            return []

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key"""
        try:
            redis = await self.get_redis()
            return await redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return -1

# Create a singleton instance
cache_manager = CacheManager() 