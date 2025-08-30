import argparse
import logging
from typing import List
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


def _parse_csv(csv_str: str) -> List[str]:
    """
    Splits a comma-separated string into a list of non-empty items, stripping whitespace.
    """
    if not csv_str:
        return []
    return [item.strip() for item in csv_str.split(",") if item.strip()]


class CommandLineArgs:
    """
    Parses command-line arguments in a manner similar to the original Ruby script.
    """

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            description="Save the content (body and replies) of a Reddit post to Markdown or HTML."
        )
        self.parser.add_argument(
            "--urls",
            type=str,
            default="",
            help="Comma-separated list of Reddit post URLs.",
        )
        self.parser.add_argument(
            "--src-files",
            type=str,
            default="",
            help="Comma-separated list of file paths containing URLs.",
        )
        self.parser.add_argument(
            "--subs",
            type=str,
            default="",
            help='Comma-separated list of subreddits (e.g., "r/python,r/askreddit").',
        )
        self.parser.add_argument(
            "--multis",
            type=str,
            default="",
            help='Comma-separated list of multireddits (e.g., "m/programming").',
        )

        self.args = self.parser.parse_args()

        self.urls: List[str] = _parse_csv(self.args.urls)
        self.src_files: List[str] = _parse_csv(self.args.src_files)
        self.subs: List[str] = _parse_csv(self.args.subs)
        self.multis: List[str] = _parse_csv(self.args.multis)

        # You can add some simple logging or validation below if needed:
        logger.info("Parsed %d URL(s) from --urls", len(self.urls))
        logger.info("Parsed %d file(s) from --src-files", len(self.src_files))
        logger.info("Parsed %d subreddit(s) from --subs", len(self.subs))
        logger.info("Parsed %d multireddit(s) from --multis", len(self.multis))
