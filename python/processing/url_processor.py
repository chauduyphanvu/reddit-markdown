import re
from typing import List, Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class UrlProcessor:
    BASE_URL = "https://www.reddit.com"

    @staticmethod
    def clean_url(url: str) -> str:
        if not url:
            return url

        url = url.split("?utm_source")[0]
        url = url.split("?ref=")[0]
        url = url.split("?context=")[0]
        url = url.rstrip("/")

        return url

    @staticmethod
    def validate_reddit_url(url: str) -> bool:
        if not url:
            return False

        # Check URL starts with https (not http)
        if not url.startswith("https://"):
            return False

        reddit_patterns = [
            r"https://(?:www\.)?reddit\.com/r/[^/]+/comments/[a-z0-9]+/",
            r"https://(?:www\.)?reddit\.com/[^/]+/comments/[a-z0-9]+/",
            r"https://(?:old\.)?reddit\.com/r/[^/]+/comments/[a-z0-9]+/",
            r"https://redd\.it/[a-z0-9]+",
        ]

        for pattern in reddit_patterns:
            if re.match(pattern, url):
                return True

        return False

    @staticmethod
    def extract_post_id(url: str) -> str:
        match = re.search(r"/comments/([a-z0-9]+)/", url)
        if match:
            return match.group(1)

        match = re.search(r"redd\.it/([a-z0-9]+)", url)
        if match:
            return match.group(1)

        parts = url.rstrip("/").split("/")
        for part in reversed(parts):
            if part and part not in ["comments", "r", "www.reddit.com", "reddit.com"]:
                return part

        return "unknown_post"

    @staticmethod
    def build_post_url(permalink: str) -> str:
        if permalink.startswith("http"):
            return permalink
        return f"{UrlProcessor.BASE_URL}{permalink}"

    @staticmethod
    def normalize_subreddit(subreddit: str) -> str:
        subreddit = subreddit.lstrip("/")
        if not subreddit.startswith("r/"):
            subreddit = f"r/{subreddit}"
        return subreddit
