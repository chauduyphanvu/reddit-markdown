import datetime
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def clean_url(url: str) -> str:
    """
    Removes trailing query parameters from a Reddit post URL,
    particularly "?utm_source" or anything that follows.

    :param url: A Reddit post URL.
    :return: Cleaned URL without extraneous query parameters.
    """
    return url.strip().split("?utm_source")[0]


def valid_url(url: str) -> bool:
    """
    Checks if the given URL matches the typical Reddit post pattern:
      https://www.reddit.com/r/<subreddit>/comments/<id>/<slug>/?

    :param url: The URL to validate.
    :return: True if the URL looks like a valid Reddit post, False otherwise.
    """
    return bool(
        re.match(r"^https:\/\/www\.reddit\.com\/r\/\w+\/comments\/\w+\/[\w_]+\/?", url)
    )


def download_post_json(url: str) -> Optional[Any]:
    """
    Appends '.json' to a Reddit post URL (if not present) and fetches the JSON data.

    :param url: The original or partially cleaned Reddit post URL.
    :return: The parsed JSON as a Python object (usually a list/dict hierarchy),
             or None if an error occurs.
    """
    json_url = url if url.endswith(".json") else url + ".json"
    req = urllib.request.Request(json_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.error("Could not download JSON for %s. Reason: %s", url, e)
        return None


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

    :param base_dir: The base directory path to save the file(s).
    :param url: The original Reddit post URL (used to derive a filename).
    :param subreddit: Subreddit name (e.g., "r/python"), which may become part of the directory structure.
    :param use_timestamped_dirs: If True, creates a new subdirectory for each unique date (from post_timestamp).
    :param post_timestamp: A string like "YYYY-MM-DD HH:MM:SS". If invalid or empty, we default to today's date.
    :param file_format: Either "md" or "html" (case-insensitive). If it's not "html", default to "md".
    :param overwrite: If True, overwrites existing files without creating a suffix (e.g., _1).
    :return: A full path to the file that does not conflict with existing files (unless overwrite=True).
    """
    name_candidate = url.rstrip("/").split("/")[-1]
    if not name_candidate:
        name_candidate = f"reddit_no_name_{int(time.time())}"

    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]  # drop "r/"

    # Format the timestamp for a subdirectory
    dt_str = ""
    if post_timestamp:
        try:
            dt = datetime.datetime.strptime(post_timestamp, "%Y-%m-%d %H:%M:%S")
            dt_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            dt_str = datetime.datetime.now().strftime("%Y-%m-%d")

    subdir = os.path.join(base_dir, subreddit) if subreddit else base_dir
    if use_timestamped_dirs and dt_str:
        subdir = os.path.join(subdir, dt_str)
    ensure_dir_exists(subdir)

    ext = file_format.lower() if file_format.lower() == "html" else "md"
    file_candidate = os.path.join(subdir, f"{name_candidate}.{ext}")

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


def markdown_to_html(md_content: str) -> str:
    """
    Converts a Markdown string to HTML.

    :param md_content: A string containing Markdown.
    :return: A string containing valid HTML representation of the original Markdown.
             If the 'markdown' package is not installed, returns a <pre> fallback.
    """
    try:
        import markdown

        return markdown.markdown(md_content)
    except ImportError:
        logger.warning("markdown package not installed; using <pre> fallback.")
        return f"<html><body><pre>{md_content}</pre></body></html>"
