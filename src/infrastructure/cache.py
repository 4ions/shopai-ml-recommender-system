from typing import Any, Optional
import hashlib
import json
import time
from functools import wraps

import diskcache

from src.config.settings import settings
from src.infrastructure.logging import get_logger
from src.infrastructure.metrics import cache_hits_total, cache_misses_total

logger = get_logger(__name__)


class Cache:
    def __init__(self, cache_type: str = "memory", redis_url: Optional[str] = None):
        self.cache_type = cache_type
        if cache_type == "disk":
            self._cache = diskcache.Cache("data/cache")
        elif cache_type == "redis" and redis_url:
            try:
                import redis
                self._cache = redis.from_url(redis_url, decode_responses=True)
            except ImportError:
                logger.warning("Redis not available, falling back to disk cache")
                self._cache = diskcache.Cache("data/cache")
        else:
            self._cache = diskcache.Cache(size_limit=1000)

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        key_data = {"args": args, "kwargs": kwargs}
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._cache.get(key)
            if value is not None:
                cache_hits_total.labels(cache_type=self.cache_type, operation="get").inc()
                if isinstance(value, str):
                    return json.loads(value)
                return value
            cache_misses_total.labels(cache_type=self.cache_type, operation="get").inc()
            return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            if ttl:
                self._cache.set(key, value, expire=ttl)
            else:
                self._cache.set(key, value)
            return True
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        try:
            return self._cache.delete(key)
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False

    def clear(self) -> bool:
        try:
            if hasattr(self._cache, "clear"):
                self._cache.clear()
            return True
        except Exception as e:
            logger.error("Cache clear error", error=str(e))
            return False


cache = Cache(
    cache_type=settings.cache_type,
    redis_url=settings.redis_url,
)


def cached(prefix: str, ttl: Optional[int] = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache._make_key(prefix, *args, **kwargs)
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator

