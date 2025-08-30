import logging
import re
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Cache for compiled regex patterns
_regex_cache: Dict[str, Optional[re.Pattern]] = {}


def _safe_compile_regex(pattern: str) -> Optional[re.Pattern]:
    """
    Safely compile a regex pattern with validation and caching.
    Prevents ReDoS attacks by limiting complexity and execution time.
    """
    if pattern in _regex_cache:
        return _regex_cache[pattern]

    # Basic validation
    if not pattern or len(pattern) > 1000:  # Reasonable length limit
        logger.warning("Regex pattern too long or empty: %s", pattern[:100])
        _regex_cache[pattern] = None
        return None

    # Check for specific dangerous patterns that cause ReDoS (refined detection)
    dangerous_patterns = [
        # Nested quantifiers - the real culprits for exponential backtracking
        r"\([^)]*\+[^)]*\)\+",  # (group+)+ patterns
        r"\([^)]*\*[^)]*\)\*",  # (group*)* patterns
        r"\([^)]*\+[^)]*\)\*",  # (group+)* patterns
        r"\([^)]*\*[^)]*\)\+",  # (group*)+ patterns
        # Deeply nested quantifiers
        r"\(\([^)]*\+[^)]*\)\+\)\+",  # ((a+)+)+ patterns
        # Alternation with overlapping patterns
        r"\([^|)]*\|[^|)]*\)\*.*\1",  # (a|ab)* where there's overlap
        # Multiple consecutive quantifiers on same element (more specific)
        r"\.\*\*|\.\+\+|\.\?\?|\+\+|\*\*",  # .**, .++, etc.
        # Catastrophic backtracking patterns
        r"\([^)]*\.[^)]*\*[^)]*\)[^)]*\.[^)]*\*",  # (.*)*.*pattern
    ]

    for dangerous in dangerous_patterns:
        try:
            if re.search(dangerous, pattern):
                logger.warning(
                    "Potentially dangerous regex pattern detected: %s", pattern
                )
                _regex_cache[pattern] = None
                return None
        except re.error:
            # If the dangerous pattern itself is invalid, skip it
            continue

    try:
        compiled = re.compile(pattern)
        _regex_cache[pattern] = compiled
        return compiled
    except re.error as e:
        logger.error("Invalid regex pattern '%s': %s", pattern, e)
        _regex_cache[pattern] = None
        return None


def _safe_regex_search(
    pattern: re.Pattern, text: str, timeout_seconds: float = 1.0
) -> bool:
    """
    Perform a regex search with timeout protection.
    """
    if not text:
        return False

    # Limit text length to prevent excessive processing
    if len(text) > 10000:
        text = text[:10000]

    start_time = time.time()
    try:
        result = pattern.search(text)
        elapsed = time.time() - start_time

        if elapsed > timeout_seconds:
            logger.warning("Regex search took too long (%.2fs), aborting", elapsed)
            return False

        return result is not None
    except Exception as e:
        logger.error("Regex search error: %s", e)
        return False


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
        if text and kw.lower() in text.lower():
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

    # Check regex with safe compilation and execution
    for rgx in filtered_regexes:
        if not rgx:  # Skip empty regex patterns
            continue

        pattern = _safe_compile_regex(rgx)
        if pattern is None:
            logger.warning("Skipping invalid regex pattern: %s", rgx)
            continue

        if text and _safe_regex_search(pattern, text):
            logger.debug("Comment filtered due to regex '%s'.", rgx)
            return filtered_message

    # No filter triggered
    return text
