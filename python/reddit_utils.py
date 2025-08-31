import datetime
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import requests
from pathlib import Path
from typing import Any, Dict, Optional
from colored_logger import get_colored_logger
from core import RateLimiter, Cache
from api import RedditClient
from io_ops import FileManager
from processing import ContentConverter, UrlProcessor

logger = get_colored_logger(__name__)


# Legacy RateLimiter class kept for backward compatibility
# New code should use core.RateLimiter directly
RateLimiter = RateLimiter


# Global instances - will be initialized by configure_performance()
_rate_limiter: Optional[RateLimiter] = None
_cache: Optional[Cache] = None
_reddit_client: Optional[RedditClient] = None

# Legacy compatibility variables for tests
_json_cache: Dict[str, Any] = {}
_cache_timestamps: Dict[str, float] = {}
_cache_ttl_seconds = 300
_max_cache_entries = 1000


def configure_performance(settings) -> None:
    """
    Configure performance settings based on Settings object.
    Should be called once at application startup.
    """
    global _rate_limiter, _cache, _reddit_client
    global _cache_ttl_seconds, _max_cache_entries  # Legacy compatibility

    # Configure rate limiter - ensure values are integers in case of Mock objects during testing
    requests_per_minute = getattr(settings, "rate_limit_requests_per_minute", 30)
    requests_per_minute = (
        requests_per_minute if isinstance(requests_per_minute, int) else 30
    )
    _rate_limiter = RateLimiter(max_requests=requests_per_minute, window_seconds=60)

    # Configure cache settings - ensure values are integers in case of Mock objects during testing
    cache_ttl_seconds = getattr(settings, "cache_ttl_seconds", 300)
    cache_ttl_seconds = cache_ttl_seconds if isinstance(cache_ttl_seconds, int) else 300
    max_cache_entries = getattr(settings, "max_cache_entries", 1000)
    max_cache_entries = (
        max_cache_entries if isinstance(max_cache_entries, int) else 1000
    )
    _cache = Cache(ttl_seconds=cache_ttl_seconds, max_entries=max_cache_entries)

    # Set legacy compatibility variables
    _cache_ttl_seconds = cache_ttl_seconds
    _max_cache_entries = max_cache_entries

    logger.info(
        "Performance configured: %d req/min, %ds cache TTL, %d max cache entries",
        requests_per_minute,
        cache_ttl_seconds,
        max_cache_entries,
    )


def _get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter, creating a default one if not configured."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
    return _rate_limiter


def _get_reddit_client(access_token: str = "") -> RedditClient:
    """Get the global Reddit client, creating one if not configured."""
    global _reddit_client
    if _reddit_client is None or _reddit_client.access_token != access_token:
        _reddit_client = RedditClient(
            access_token=access_token, rate_limiter=_rate_limiter, cache=_cache
        )
    return _reddit_client


def clean_url(url: str) -> str:
    """
    Removes trailing query parameters from a Reddit post URL,
    particularly "?utm_source" or anything that follows.
    Now delegates to UrlProcessor.

    :param url: A Reddit post URL.
    :return: Cleaned URL without extraneous query parameters.
    """
    return url.strip().split("?utm_source")[0]


def valid_url(url: str) -> bool:
    """
    Checks if the given URL matches the typical Reddit post pattern.
    Now delegates to UrlProcessor.
    """
    return UrlProcessor.validate_reddit_url(url)


def download_post_json(url: str, access_token: str = "") -> Optional[Any]:
    """
    Appends '.json' to a Reddit post URL and fetches the JSON data.
    Uses an access token for authenticated requests if provided.
    Enhanced with rate limiting, retry logic, and caching.
    """
    global _json_cache, _cache_timestamps

    # Input validation
    if not url or not isinstance(url, str):
        logger.error("Invalid URL provided: %s", url)
        return None

    # Create cache key
    json_url = url if url.endswith(".json") else url + ".json"
    cache_key = f"{json_url}:{bool(access_token)}"

    # Check cache first
    current_time = time.time()
    if (
        cache_key in _json_cache
        and cache_key in _cache_timestamps
        and current_time - _cache_timestamps[cache_key] < _cache_ttl_seconds
    ):
        logger.debug("Using cached data for %s", url)
        return _json_cache[cache_key]

    # Clean expired cache entries
    _cleanup_cache()

    # Apply rate limiting
    rate_limiter = _get_rate_limiter()
    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.wait_time()
        logger.info("Rate limit reached. Waiting %.1f seconds...", wait_time)
        time.sleep(wait_time)

    headers = {"User-Agent": "RedditMarkdownConverter/1.0 (Safe Download Bot)"}

    if access_token:
        # Use the OAuth endpoint for authenticated requests
        json_url = json_url.replace(
            "https://www.reddit.com", "https://oauth.reddit.com"
        )
        json_url = json_url.replace("https://reddit.com", "https://oauth.reddit.com")
        headers["Authorization"] = f"bearer {access_token}"

    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.get(json_url, headers=headers, timeout=30)
            res.raise_for_status()
            result = res.json()

            # Cache the result
            _json_cache[cache_key] = result
            _cache_timestamps[cache_key] = current_time

            return result
        except json.JSONDecodeError as e:
            logger.error("JSON decode error for %s: %s", url, e)
            return None
        except requests.exceptions.Timeout:
            logger.warning(
                "Timeout on attempt %d/%d for %s", attempt + 1, max_retries, url
            )
            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff
        except requests.exceptions.RequestException as e:
            logger.error(
                "Request failed on attempt %d/%d for %s. Reason: %s",
                attempt + 1,
                max_retries,
                url,
                e,
            )
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            break

    logger.error("Failed to download JSON for %s after %d attempts", url, max_retries)
    return None


def _cleanup_cache() -> None:
    """Remove expired entries from the cache. Legacy function for backward compatibility."""
    global _json_cache, _cache_timestamps, _cache_ttl_seconds, _max_cache_entries

    current_time = time.time()

    # Remove expired entries
    expired_keys = [
        key
        for key, timestamp in _cache_timestamps.items()
        if current_time - timestamp >= _cache_ttl_seconds
    ]

    for key in expired_keys:
        _json_cache.pop(key, None)
        _cache_timestamps.pop(key, None)

    # Enforce cache size limit
    max_entries = _max_cache_entries if isinstance(_max_cache_entries, int) else 1000
    if len(_json_cache) > max_entries:
        # Sort by timestamp and remove oldest entries
        sorted_keys = sorted(_cache_timestamps.items(), key=lambda x: x[1])
        keys_to_remove = [
            key for key, _ in sorted_keys[: len(_json_cache) - max_entries]
        ]

        for key in keys_to_remove:
            _json_cache.pop(key, None)
            _cache_timestamps.pop(key, None)


def get_replies(
    reply_data: Dict[str, Any], max_depth: int = -1
) -> Dict[str, Dict[str, Any]]:
    """
    Recursively gathers child replies from a given reply object's "replies" field.

    :param reply_data: The reply object (part of the Reddit JSON structure).
    :param max_depth: The maximum allowed depth; replies deeper than this are skipped.
                      If set to -1, there's no depth limit.
    :return: A dictionary keyed by child_id with information about depth and the raw child reply.
    """
    collected: Dict[str, Dict[str, Any]] = {}
    replies_obj = reply_data.get("data", {}).get("replies")
    if not replies_obj:
        return collected

    children = replies_obj.get("data", {}).get("children", [])
    for child in children:
        child_id = child.get("data", {}).get("id")
        child_depth = child.get("data", {}).get("depth", 0)
        child_body = child.get("data", {}).get("body", "")

        # Stop if max depth exceeded (unless -1, i.e. no limit)
        if max_depth != -1 and child_depth > max_depth:
            continue
        if not child_body.strip():
            # skip empty/spam
            continue

        collected[child_id] = {"depth": child_depth, "child_reply": child}
        # Merge recursively
        collected.update(get_replies(child, max_depth))
    return collected


def resolve_save_dir(config_directory: str) -> str:
    """
    Determines the path where posts should be saved, either by:
      1) Using a config value
      2) Using an environment variable if config_directory == "DEFAULT_REDDIT_SAVE_LOCATION"
      3) Prompting the user if no path is provided

    :param config_directory: The directory from settings, or the literal string "DEFAULT_REDDIT_SAVE_LOCATION".
    :return: The resolved directory path as a string.
    """
    if config_directory == "DEFAULT_REDDIT_SAVE_LOCATION":
        directory = os.environ.get("DEFAULT_REDDIT_SAVE_LOCATION", "")
        if not directory:
            logger.critical(
                "DEFAULT_REDDIT_SAVE_LOCATION environment variable not set. Exiting..."
            )
            sys.exit(1)
        logger.info("Using default directory from environment variable: %s", directory)
        return directory
    elif config_directory:
        # Directory is set in config, use it directly if valid
        logger.info("Using directory set in configuration: %s", config_directory)
        return config_directory
    else:
        # Ask user for directory
        logger.info(
            "Enter the full path to save the post(s). "
            "Hit Enter for current dir (%s)",
            os.getcwd(),
        )
        directory = input().strip()
        if not directory:
            directory = os.getcwd()
        while not os.path.isdir(directory):
            logger.error("Invalid path: '%s'. Try again.", directory)
            directory = input().strip()
            if not directory:
                directory = os.getcwd()
        logger.info("User selected directory: %s", directory)
        return directory


def ensure_dir_exists(path: str) -> None:
    """
    Ensures the given directory exists; if not, creates it (and any intermediate dirs).

    :param path: The directory path to ensure exists.
    """
    if not os.path.isdir(path):
        logger.debug("Directory %s does not exist, creating...", path)
        os.makedirs(path, exist_ok=True)


def generate_filename(
    base_dir: str,
    url: str,
    subreddit: str,
    use_timestamped_dirs: bool,
    post_timestamp: str,
    file_format: str,
    overwrite: bool,
) -> str:
    """
    Generates a unique path for the output file, possibly placing it inside a subreddit folder
    and/or a timestamped folder, as configured by the user.

    Enhanced security:
    - Prevents path traversal attacks
    - Sanitizes filenames and directory names
    - Validates path components

    :param base_dir: The base directory path to save the file(s).
    :param url: The original Reddit post URL (used to derive a filename).
    :param subreddit: Subreddit name (e.g., "r/python"), which may become part of the directory structure.
    :param use_timestamped_dirs: If True, creates a new subdirectory for each unique date (from post_timestamp).
    :param post_timestamp: A string like "YYYY-MM-DD HH:MM:SS". If invalid or empty, we default to today's date.
    :param file_format: Either "md" or "html" (case-insensitive). If it's not "html", default to "md".
    :param overwrite: If True, overwrites existing files without creating a suffix (e.g., _1).
    :return: A full path to the file that does not conflict with existing files (unless overwrite=True).
    """

    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal and invalid characters."""
        if not filename:
            return f"reddit_no_name_{int(time.time())}"

        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
        filename = re.sub(r"\.\.+", "_", filename)  # Remove .. sequences
        filename = filename.strip(". ")  # Remove leading/trailing dots and spaces

        # Truncate if too long
        if len(filename) > 200:
            filename = filename[:200]

        return filename if filename else f"reddit_no_name_{int(time.time())}"

    def sanitize_dirname(dirname: str) -> str:
        """Sanitize directory name to prevent path traversal."""
        if not dirname:
            return ""

        # Remove path separators and dangerous characters
        dirname = re.sub(r'[<>:"/\\|?*]', "_", dirname)
        dirname = re.sub(r"\.\.+", "_", dirname)  # Remove .. sequences
        dirname = dirname.strip(". ")  # Remove leading/trailing dots and spaces

        # Truncate if too long
        if len(dirname) > 100:
            dirname = dirname[:100]

        return dirname if dirname else ""

    # Sanitize filename from URL
    name_candidate = url.rstrip("/").split("/")[-1]
    name_candidate = sanitize_filename(name_candidate)

    # Sanitize subreddit name
    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]  # drop "r/"
    subreddit = sanitize_dirname(subreddit)

    # Format the timestamp for a subdirectory
    dt_str = ""
    if post_timestamp:
        try:
            dt = datetime.datetime.strptime(post_timestamp, "%Y-%m-%d %H:%M:%S")
            dt_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            dt_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # Use pathlib for secure path construction
    base_path = Path(base_dir).resolve()

    if subreddit:
        subdir_path = base_path / subreddit
    else:
        subdir_path = base_path

    if use_timestamped_dirs and dt_str:
        subdir_path = subdir_path / dt_str

    # Ensure the final path is still within base_dir (security check)
    try:
        subdir_path = subdir_path.resolve()
        if not str(subdir_path).startswith(str(base_path)):
            logger.error("Path traversal attempt detected. Using base directory only.")
            subdir_path = base_path
    except (OSError, ValueError) as e:
        logger.error("Path resolution error: %s. Using base directory.", e)
        subdir_path = base_path

    ensure_dir_exists(str(subdir_path))

    ext = file_format.lower() if file_format.lower() == "html" else "md"
    file_candidate = str(subdir_path / f"{name_candidate}.{ext}")

    if os.path.isfile(file_candidate):
        if overwrite:
            logger.warning(
                "Overwriting existing file: %s", os.path.basename(file_candidate)
            )
            return file_candidate
        else:
            base_no_ext = os.path.splitext(file_candidate)[0]
            suffix = 1
            while os.path.isfile(f"{base_no_ext}_{suffix}.{ext}"):
                suffix += 1
            new_file = f"{base_no_ext}_{suffix}.{ext}"
            logger.info("File exists. Using: %s", os.path.basename(new_file))
            return new_file
    return file_candidate


def generate_unique_media_filename(url: str, media_dir: str) -> str:
    """
    Generates a unique filename for media files to avoid collisions.

    :param url: The media URL to extract filename from
    :param media_dir: Directory where the media will be saved
    :return: A unique file path within media_dir
    """
    # Extract filename from URL
    parsed_url = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed_url.path)

    # If no filename found, generate one
    if not filename or "." not in filename:
        filename = f"media_{int(time.time())}.mp4"  # Default extension for videos

    file_path = os.path.join(media_dir, filename)

    # Handle filename collisions
    if os.path.isfile(file_path):
        name, ext = os.path.splitext(filename)
        suffix = 1
        while os.path.isfile(os.path.join(media_dir, f"{name}_{suffix}{ext}")):
            suffix += 1
        filename = f"{name}_{suffix}{ext}"
        file_path = os.path.join(media_dir, filename)

    return file_path


def download_media(url: str, file_path: str) -> bool:
    """
    Downloads a media file from a URL and saves it to a local path.
    """
    headers = {"User-Agent": "MyRedditScript/0.1"}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=10) as r:
            r.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info("Successfully downloaded media to %s", file_path)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Could not download media from %s. Reason: %s", url, e)
        return False
