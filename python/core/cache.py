import time
from typing import Any, Dict, Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class Cache:
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 1000):
        self.ttl_seconds = ttl_seconds if isinstance(ttl_seconds, int) else 300
        self.max_entries = max_entries if isinstance(max_entries, int) else 1000
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        if time.time() - self._timestamps[key] > self.ttl_seconds:
            del self._cache[key]
            del self._timestamps[key]
            return None

        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.max_entries:
            oldest_key = min(self._timestamps, key=self._timestamps.get)
            del self._cache[oldest_key]
            del self._timestamps[oldest_key]

        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()

    def size(self) -> int:
        return len(self._cache)
