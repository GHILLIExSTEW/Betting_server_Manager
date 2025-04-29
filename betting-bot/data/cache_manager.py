import logging
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir: str = 'data/cache'):
        self.cache_dir = cache_dir
        self._ensure_cache_directory()
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

    def _ensure_cache_directory(self):
        """Ensure the cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.cache_dir, f"{key}.json")

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache with optional TTL."""
        cache_data = {
            'value': value,
            'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat() if ttl else None
        }
        
        # Store in memory
        self.memory_cache[key] = cache_data
        
        # Store in file
        try:
            with open(self._get_cache_path(key), 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Error writing to cache file: {str(e)}")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        # Check memory cache first
        if key in self.memory_cache:
            cache_data = self.memory_cache[key]
            if self._is_valid(cache_data):
                return cache_data['value']
            else:
                del self.memory_cache[key]

        # Check file cache
        try:
            with open(self._get_cache_path(key), 'r') as f:
                cache_data = json.load(f)
                if self._is_valid(cache_data):
                    # Update memory cache
                    self.memory_cache[key] = cache_data
                    return cache_data['value']
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error reading from cache file: {str(e)}")
            return None

    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        # Remove from memory
        self.memory_cache.pop(key, None)
        
        # Remove from file
        try:
            os.remove(self._get_cache_path(key))
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Error deleting cache file: {str(e)}")

    def _is_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid."""
        if cache_data['expires_at'] is None:
            return True
            
        try:
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            return datetime.now() < expires_at
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all cached data."""
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear file cache
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}") 