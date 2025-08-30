import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _load_env_file(env_path: str) -> None:
    """
    Simple .env file parser that doesn't require external dependencies.
    Loads key=value pairs from .env file into os.environ.
    """
    if not os.path.isfile(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)  # Split on first = only
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]

                    # .env file takes precedence over system environment variables
                    if key:
                        os.environ[key] = value

        logger.info(".env file loaded successfully (built-in parser)")

    except Exception as e:
        logger.warning("Failed to load .env file: %s", e)


# Try to load .env files using built-in parser (no external dependencies required)
_env_file_paths = [".env", "../.env"]
for env_path in _env_file_paths:
    if os.path.isfile(env_path):
        _load_env_file(env_path)
        break


class Settings:
    """
    Manages loading and validation of settings from a JSON file (by default `settings.json`).
    It also optionally checks GitHub for a newer release version.
    """

    def __init__(self, settings_file: str = "../settings.json") -> None:
        """
        Loads settings from the specified file, then populates instance variables.
        Exits the program if the file is missing or invalid.

        :param settings_file: The path to `settings.json`. Defaults to "../settings.json".
        """
        if not os.path.isfile(settings_file):
            logger.critical(
                "settings.json not found at '%s'. Exiting...", settings_file
            )
            sys.exit(1)

        self.raw = self._load_json(settings_file)
        if not self.raw:
            logger.critical("settings.json appears to be empty or invalid. Exiting...")
            sys.exit(1)

        # Basic config
        self.version: str = self.raw.get("version", "0.0.0")
        self.file_format: str = self.raw.get("file_format", "md")
        self.update_check_on_startup: bool = self.raw.get(
            "update_check_on_startup", True
        )
        self.show_auto_mod_comment: bool = self.raw.get("show_auto_mod_comment", True)
        self.line_break_between_parent_replies: bool = self.raw.get(
            "line_break_between_parent_replies", True
        )
        self.show_upvotes: bool = self.raw.get("show_upvotes", True)
        self.reply_depth_color_indicators: bool = self.raw.get(
            "reply_depth_color_indicators", True
        )
        self.reply_depth_max: int = self.raw.get("reply_depth_max", -1)
        self.overwrite_existing_file: bool = self.raw.get(
            "overwrite_existing_file", False
        )
        self.save_posts_by_subreddits: bool = self.raw.get(
            "save_posts_by_subreddits", False
        )
        self.show_timestamp: bool = self.raw.get("show_timestamp", True)
        self.use_timestamped_directories: bool = self.raw.get(
            "use_timestamped_directories", False
        )
        self.enable_media_downloads: bool = self.raw.get("enable_media_downloads", True)

        # Auth settings - credentials now read from environment variables for security
        auth_settings = self.raw.get("auth", {})
        self.login_on_startup: bool = auth_settings.get("login_on_startup", False)

        # Read credentials from .env file (loaded into environment)
        self.client_id: str = os.environ.get("REDDIT_CLIENT_ID", "")
        self.client_secret: str = os.environ.get("REDDIT_CLIENT_SECRET", "")
        self.username: str = os.environ.get("REDDIT_USERNAME", "")
        self.password: str = os.environ.get("REDDIT_PASSWORD", "")

        # Warn if credentials are not set or still using placeholders
        placeholder_patterns = [
            "your_actual_client_id_here",
            "your_id",
            "83eZtNGTIaaJdIyhD3-4ow",
            "5ymZetfCvPgF7OXZlj2dtQ",
        ]

        if self.login_on_startup and (
            not self.client_id
            or not self.client_secret
            or self.client_id in placeholder_patterns
            or self.client_secret.startswith("d3yMniPx")
            or self.client_secret.startswith("YWr9wmbHD")
        ):
            logger.warning(
                "Login enabled but valid credentials not found in .env file."
            )
            logger.warning("Steps to fix:")
            logger.warning(
                "1. Create a Reddit app at https://www.reddit.com/prefs/apps/"
            )
            logger.warning(
                "2. Replace placeholder values in .env file with real credentials"
            )
            logger.warning("3. Restart the application")

        # Filtering options
        self.filtered_message: str = self.raw.get("filtered_message", "Filtered")
        self.filtered_keywords = self.raw.get("filters", {}).get("keywords", [])
        self.filtered_min_upvotes: int = self.raw.get("filters", {}).get(
            "min_upvotes", 0
        )
        self.filtered_authors = self.raw.get("filters", {}).get("authors", [])
        self.filtered_regexes = self.raw.get("filters", {}).get("regexes", [])

        # Performance settings
        performance_settings = self.raw.get("performance", {})
        self.cache_ttl_seconds: int = performance_settings.get("cache_ttl_seconds", 300)
        self.max_cache_entries: int = performance_settings.get(
            "max_cache_entries", 1000
        )
        self.rate_limit_requests_per_minute: int = performance_settings.get(
            "rate_limit_requests_per_minute", 30
        )

        # Additional settings
        self.default_save_location: str = self.raw.get("default_save_location", "")
        self.multi_reddits: Dict[str, Any] = self.raw.get("multi_reddits", {})

        logger.info("Settings loaded from '%s'.", settings_file)

        # Check for updates if enabled
        if self.update_check_on_startup:
            self.check_for_updates()

    def _load_json(self, path: str) -> Any:
        """
        Loads JSON from the given file path.

        :param path: The path to the JSON file.
        :return: The parsed JSON (dictionary or list) if valid, otherwise None.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.error("Error loading JSON file '%s': %s", path, e)
            return None

    def check_for_updates(self) -> None:
        """
        Optionally checks if a newer version is available on GitHub by querying
        the GitHub Release endpoint for the repository. Logs a suggestion if a new
        version is found.
        """
        check_url = (
            "https://api.github.com/repos/chauduyphanvu/reddit-markdown/releases"
        )
        logger.debug("Checking for updates at %s", check_url)
        try:
            req = urllib.request.Request(
                check_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())

            if not data:
                logger.warning(
                    "Could not fetch release info from GitHub. Please check manually."
                )
                return

            latest_tag = data[0].get("tag_name", "0.0.0")
            if re.match(r"^\d+\.\d+\.\d+$", latest_tag):
                from packaging.version import Version

                if Version(latest_tag) > Version(self.version):
                    logger.info(
                        "A new version (%s) is available. You have %s. "
                        "Download it from https://github.com/chauduyphanvu/reddit-markdown.",
                        latest_tag,
                        self.version,
                    )
                else:
                    logger.debug("Current version %s is up-to-date.", self.version)
            else:
                logger.warning(
                    "GitHub returned an invalid version number: %s", latest_tag
                )
        except Exception as e:
            logger.error("Could not check for updates: %s", e)
