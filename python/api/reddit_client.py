import json
import logging
import requests
from typing import Any, Dict, Optional
from colored_logger import get_colored_logger
from core import Cache, RateLimiter

logger = get_colored_logger(__name__)


class RedditClient:
    BASE_URL = "https://www.reddit.com"
    OAUTH_BASE_URL = "https://oauth.reddit.com"
    USER_AGENT = "RedditMarkdownConverter/1.0 (Safe Download Bot)"

    def __init__(
        self,
        access_token: str = "",
        rate_limiter: Optional[RateLimiter] = None,
        cache: Optional[Cache] = None,
    ):
        self.access_token = access_token
        self.rate_limiter = rate_limiter or RateLimiter(
            max_requests=30, window_seconds=60
        )
        self.cache = cache or Cache(ttl_seconds=300, max_entries=1000)

    def download_post_json(self, url: str) -> Optional[Any]:
        if not url:
            return None

        if not url.endswith(".json"):
            if "?" in url:
                base, params = url.split("?", 1)
                url = f"{base}.json?{params}"
            else:
                url = f"{url}.json"

        cached_data = self.cache.get(url)
        if cached_data is not None:
            logger.debug("Using cached data for %s", url)
            return cached_data

        self.rate_limiter.wait_if_needed()

        headers = {"User-Agent": self.USER_AGENT}
        if self.access_token:
            headers["Authorization"] = f"bearer {self.access_token}"
            if url.startswith(self.BASE_URL):
                url = url.replace(self.BASE_URL, self.OAUTH_BASE_URL)

        try:
            logger.debug("Downloading JSON from %s", url)
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            self.cache.set(url, data)
            return data

        except requests.exceptions.RequestException as e:
            logger.error("Failed to download %s: %s", url, e)
            return None
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from %s: %s", url, e)
            return None

    def fetch_subreddit_posts(
        self, subreddit: str, listing: str = "best", limit: int = 25
    ) -> Optional[Dict[str, Any]]:
        subreddit = subreddit.lstrip("/")
        base = self.OAUTH_BASE_URL if self.access_token else self.BASE_URL
        url = f"{base}/{subreddit}/{listing}?limit={limit}"

        return self.download_post_json(url)
