#!/usr/bin/env python3

from __future__ import (
    annotations,
)

import logging
from pathlib import Path
from typing import List

import reddit_utils as utils
from cli_args import CommandLineArgs
from post_renderer import build_post_content
from settings import Settings
from url_fetcher import UrlFetcher

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Orchestrates the entire flow:
    1. Load settings
    2. Parse CLI args
    3. Fetch & clean Reddit post URLs
    4. Resolve output directory
    5. Process each URL (download, render, save)
    """
    settings = _load_settings()
    cli_args = _parse_cli_args()
    all_urls = _fetch_urls(settings, cli_args)
    base_save_dir = utils.resolve_save_dir(settings.default_save_location)
    _process_all_urls(all_urls, settings, base_save_dir)

    logger.info("Thanks for using this script!")
    logger.info("If you have issues, open an issue on GitHub:")
    logger.info("https://github.com/chauduyphanvu/reddit-markdown/issues")


def _load_settings() -> Settings:
    """
    Loads the Settings object from the JSON file and optionally checks for updates.
    """
    settings = Settings()
    if settings.update_check_on_startup:
        settings.check_for_updates()
    return settings


def _parse_cli_args() -> CommandLineArgs:
    """
    Parses and returns the command-line arguments.
    """
    return CommandLineArgs()


def _fetch_urls(settings: Settings, cli_args: CommandLineArgs) -> List[str]:
    """
    Uses UrlFetcher to gather the final list of Reddit post URLs, then cleans them.
    """
    fetcher = UrlFetcher(settings, cli_args)
    return [utils.clean_url(u) for u in fetcher.urls if u]


def _process_all_urls(
    all_urls: List[str], settings: Settings, base_save_dir: str
) -> None:
    """
    Iterates over the list of URLs and processes each (download, render, and save).
    """
    colors = ["🟩", "🟨", "🟧", "🟦", "🟪", "🟥", "🟫", "⬛️", "⬜️"]
    for i, url in enumerate(all_urls, 1):
        _process_single_url(
            index=i,
            url=url,
            total=len(all_urls),
            settings=settings,
            base_save_dir=base_save_dir,
            colors=colors,
        )


def _process_single_url(
    *,
    index: int,
    url: str,
    total: int,
    settings: Settings,
    base_save_dir: str,
    colors: List[str],
) -> None:
    """
    Handles the downloading of JSON data for a single Reddit URL,
    rendering post content, and saving it to the specified location.
    """
    if not utils.valid_url(url):
        logger.warning("Invalid post URL '%s'. Skipping...", url)
        return

    logger.info("Processing post %d of %d: %s", index, total, url)
    data = utils.download_post_json(url)
    if not data or len(data) < 2:
        logger.error("Could not fetch or parse post data for %s. Skipping...", url)
        return

    post_info = data[0].get("data", {}).get("children", [])
    if not post_info:
        logger.error("No post info found for %s. Skipping...", url)
        return
    post_data = post_info[0].get("data", {})

    # The replies (index 1)
    replies_data = data[1].get("data", {}).get("children", [])

    # Build the content in Markdown
    raw_markdown = build_post_content(
        post_data=post_data,
        replies_data=replies_data,
        settings=settings,
        colors=colors,
        url=url,
    )

    # Convert to HTML if required
    if settings.file_format.lower() == "html":
        final_content = utils.markdown_to_html(raw_markdown)
    else:
        final_content = raw_markdown

    # Derive timestamp if needed
    from datetime import datetime

    post_timestamp = ""
    if "created_utc" in post_data:
        dt = datetime.utcfromtimestamp(post_data["created_utc"])
        post_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

    # Generate a filename and save the file
    target_path = utils.generate_filename(
        base_dir=base_save_dir,
        url=url,
        subreddit=post_data.get("subreddit_name_prefixed", ""),
        use_timestamped_dirs=settings.use_timestamped_directories,
        post_timestamp=post_timestamp,
        file_format=settings.file_format,
        overwrite=settings.overwrite_existing_file,
    )

    logger.info("Saving post to %s", target_path)
    _write_to_file(Path(target_path), final_content)

    logger.info("Reddit post saved at %s.", target_path)
    logger.info("---")


def _write_to_file(file_path: Path, content: str) -> None:
    """
    Writes the given content to the specified file path.
    Using pathlib.Path for file operations is a modern best practice.
    """
    # Ensure parent directories exist (like in "ensure_dir_exists")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
