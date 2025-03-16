import logging
import re
from typing import List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def apply_filter(
    author: str,
    text: str,
    upvotes: int,
    filtered_keywords: List[str],
    filtered_authors: List[str],
    min_upvotes: int,
    filtered_regexes: List[str],
    filtered_message: str,
) -> str:
    """
    Applies user-defined filters to a reply. If the content matches any filter,
    it returns `filtered_message`; otherwise it returns the original `text`.

    :param author: The username of the reply's author.
    :param text: The body of the reply/comment.
    :param upvotes: The upvote count for the comment.
    :param filtered_keywords: Case-insensitive keywords that trigger filtering.
    :param filtered_authors: Authors to filter regardless of content.
    :param min_upvotes: Minimum upvotes required; replies below this get filtered.
    :param filtered_regexes: Regex patterns. If any match, we filter out the reply.
    :param filtered_message: The string to return if filtering is triggered.
    :return: Either the original text or the `filtered_message` if any filter matches.
    """

    # Check keywords
    for kw in filtered_keywords:
        if kw.lower() in text.lower():
            logger.debug("Comment filtered due to keyword '%s'.", kw)
            return filtered_message

    # Check authors
    if author in filtered_authors:
        logger.debug(
            "Comment filtered because author '%s' is in filtered_authors.", author
        )
        return filtered_message

    # Check upvotes
    if upvotes < min_upvotes:
        logger.debug(
            "Comment filtered because upvotes (%d) is less than min_upvotes (%d).",
            upvotes,
            min_upvotes,
        )
        return filtered_message

    # Check regex
    for rgx in filtered_regexes:
        pattern = re.compile(rgx)
        if pattern.search(text):
            logger.debug("Comment filtered due to regex '%s'.", rgx)
            return filtered_message

    # No filter triggered
    return text
