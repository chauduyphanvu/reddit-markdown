import csv
import json
import logging
import os
import random
import requests
from typing import Any, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class UrlFetcher:
    """
    Converts subreddits / multireddits / local files to an actual set of Reddit post URLs.
    If no arguments are given, it will prompt the user for input (similar to the Ruby script).
    """

    BASE_URL: str = "https://www.reddit.com"
    OAUTH_BASE_URL: str = "https://oauth.reddit.com"

    def __init__(self, settings: Any, cli_args: Any, access_token: str = "") -> None:
        """
        Initializes the UrlFetcher with settings and CLI arguments, then populates
        self.urls with any found from direct arguments, files, subreddits, or multireddits.

        :param settings: The Settings object with relevant config (e.g., multi_reddits).
        :param cli_args: The CommandLineArgs object containing user CLI input.
        :param access_token: The OAuth access token for authenticated requests.
        """
        self.settings = settings
        self.cli_args = cli_args
        self.access_token = access_token
        self.urls: List[str] = []

        # Convert CLI arguments to actual post links
        self._collect_urls()

        # If no arguments provided, ask user for input
        if not self.urls:
            self._prompt_for_input()

    def _collect_urls(self) -> None:
        """
        Collects all URLs from CLI arguments: direct URLs, file-sourced URLs,
        subreddit-based links, and multireddits.
        """
        # 1) Direct URLs
        self.urls.extend(self.cli_args.urls)

        # 2) URLs from source files
        for file_path in self.cli_args.src_files:
            self.urls.extend(self._urls_from_file(file_path))

        # 3) Subreddit mode
        for subreddit in self.cli_args.subs:
            self.urls.extend(self._get_subreddit_posts(subreddit))

        # 4) Multireddit mode
        for multi_name in self.cli_args.multis:
            sub_list = self.settings.multi_reddits.get(multi_name, [])
            if not sub_list:
                logger.warning(
                    "No subreddits found for '%s' in settings.json.", multi_name
                )
            else:
                for sub in sub_list:
                    self.urls.extend(self._get_subreddit_posts(sub))

    def _urls_from_file(self, file_path: str) -> List[str]:
        """
        Reads a file containing one or more rows of comma-separated URLs.

        :param file_path: The path to the file containing URLs.
        :return: A list of extracted URLs.
        """
        result: List[str] = []
        if not os.path.isfile(file_path):
            logger.error("File '%s' not found. Skipping...", file_path)
            return result

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    # Each row can contain multiple comma-separated URLs
                    for url in row:
                        candidate = url.strip()
                        if candidate:
                            result.append(candidate)
        except Exception as e:
            logger.error("Error reading file '%s': %s", file_path, e)
        return result

    def _prompt_for_input(self) -> None:
        """
        Prompts the user for input if no URLs were supplied. Accepts direct URLs or keywords
        like 'demo', 'surprise', 'r/<subreddit>', or 'm/<multireddit>' to trigger special behaviors.
        """
        logger.info(
            "Enter/paste the Reddit link(s), comma-separated. Or 'demo', 'surprise', 'r/subreddit', or 'm/multireddit':"
        )
        user_in = input().strip()
        while not user_in:
            logger.error("No input provided. Try again.")
            user_in = input().strip()

        self.urls = self._interpret_input_mode(user_in)

    def _interpret_input_mode(self, user_in: str) -> List[str]:
        """
        Interprets the user's input. Special modes include:
          - 'demo'
          - 'surprise'
          - subreddits starting with "r/"
          - multireddits starting with "m/"

        :param user_in: The raw user input string.
        :return: A list of URLs.
        """
        lower_in = user_in.lower()
        if lower_in == "demo":
            logger.info("Demo mode enabled.")
            return [
                "https://www.reddit.com/r/pcmasterrace/comments/101kjyq/my_dad_has_been_playing_civilization_almost_daily/"
            ]
        elif lower_in == "surprise":
            logger.info(
                "Surprise mode enabled. Grabbing one random post from r/popular."
            )
            return self._fetch_posts_from_sub("r/popular", pick_random=True)
        elif user_in.startswith("r/"):
            logger.info("Subreddit mode: fetching best posts from %s ...", user_in)
            return self._get_subreddit_posts(user_in, best=True)
        elif user_in.startswith("m/"):
            logger.info(
                "Multireddit mode: attempting to fetch subreddits from settings for %s ...",
                user_in,
            )
            subs = self.settings.multi_reddits.get(user_in, [])
            results: List[str] = []
            for s in subs:
                results.extend(self._get_subreddit_posts(s, best=True))
            return results
        else:
            # Just a direct link or multiple links
            return [x.strip() for x in user_in.split(",") if x.strip()]

    def _get_subreddit_posts(self, subreddit_str: str, best: bool = True) -> List[str]:
        """
        Fetch multiple posts from a given subreddit.
        If best=True, uses /best; otherwise returns random posts from the listing.

        :param subreddit_str: The 'r/<subreddit>' string.
        :param best: Whether to use the /best endpoint or not.
        :return: A list of Reddit post URLs from that subreddit.
        """
        return self._fetch_posts_from_sub(subreddit_str, pick_random=False, best=best)

    def _fetch_posts_from_sub(
        self, subreddit_str: str, pick_random: bool = False, best: bool = False
    ) -> List[str]:
        """
        Fetches posts from a subreddit listing. Optionally picks one at random.

        :param subreddit_str: The subreddit string (e.g. "r/python").
        :param pick_random: If True, picks one random post from the fetched list.
        :param best: If True, uses '/best' listing to fetch top posts.
        :return: A list of post URLs.
        """
        subreddit_str = subreddit_str.lstrip("/")  # remove leading slash if present
        
        base = self.OAUTH_BASE_URL if self.access_token else self.BASE_URL
        url = f"{base}/{subreddit_str}"

        if best:
            url += "/best"

        json_data = self._download_post_json(url)
        if not json_data or "data" not in json_data:
            logger.error("Unable to fetch data from %s. Skipping...", url)
            return []

        children = json_data["data"].get("children", [])
        post_links: List[str] = []
        for child in children:
            permalink = child["data"].get("permalink")
            if permalink:
                post_links.append(self.BASE_URL + permalink)

        if pick_random and post_links:
            return [random.choice(post_links)]
        return post_links

    def _download_post_json(self, url: str) -> Optional[Any]:
        """
        Helper that tries to fetch JSON from a subreddit listing or post URL (with `.json` appended).

        :param url: The subreddit or post URL (without or with '.json').
        :return: The parsed JSON if successful, otherwise None.
        """
        json_url = url if url.endswith(".json") else url + ".json"
        headers = {"User-Agent": "MyRedditScript/0.1"}
        if self.access_token:
            headers["Authorization"] = f"bearer {self.access_token}"

        try:
            res = requests.get(json_url, headers=headers, timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to download JSON data for %s: %s", url, e)
            return None
