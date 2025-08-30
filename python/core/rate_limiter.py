import time
from typing import List
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests if isinstance(max_requests, int) else 60
        self.window_seconds = window_seconds if isinstance(window_seconds, int) else 60
        self.requests: List[float] = []

    def is_allowed(self) -> bool:
        now = time.time()
        self.requests = [
            req_time
            for req_time in self.requests
            if now - req_time < self.window_seconds
        ]

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

    def wait_time(self) -> float:
        if not self.requests:
            return 0
        return max(0, self.window_seconds - (time.time() - self.requests[0]))

    def wait_if_needed(self) -> None:
        if not self.is_allowed():
            wait = self.wait_time()
            if wait > 0:
                logger.debug("Rate limit reached. Waiting %.2f seconds...", wait)
                time.sleep(wait)
