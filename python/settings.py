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
        self.enable_media_downloads: bool = self.raw.get(
            "enable_media_downloads", True
        )

        # Filtering options
        self.filtered_message: str = self.raw.get("filtered_message", "Filtered")
        self.filtered_keywords = self.raw.get("filters", {}).get("keywords", [])
        self.filtered_min_upvotes: int = self.raw.get("filters", {}).get(
            "min_upvotes", 0
        )
        self.filtered_authors = self.raw.get("filters", {}).get("authors", [])
        self.filtered_regexes = self.raw.get("filters", {}).get("regexes", [])

        # Additional settings
        self.default_save_location: str = self.raw.get("default_save_location", "")
        self.multi_reddits: Dict[str, Any] = self.raw.get("multi_reddits", {})

        logger.info("Settings loaded from '%s'.", settings_file)

    def _load_json(self, path: str) -> Any:
        """
        Loads JSON from the given file path.

        :param path: The path to the JSON file.
        :return: The parsed JSON (dictionary or list) if valid, otherwise None.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error("JSON decoding error for '%s': %s", path, e)
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
                from distutils.version import LooseVersion

                if LooseVersion(latest_tag) > LooseVersion(self.version):
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
