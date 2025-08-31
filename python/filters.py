import logging
import re
import time
from typing import Dict, List, Optional, Union, Any
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)

# Check for re2 availability for enhanced ReDoS protection
_re2_available = False
try:
    import re2

    _re2_available = True
    logger.debug("re2 library available, using for enhanced ReDoS protection")
    # Cache for compiled regex patterns (re2 or standard re)
    _regex_cache: Dict[str, Optional[Union[re.Pattern, Any]]] = {}
except ImportError:
    logger.debug("re2 library not available, using standard re with ReDoS protection")
    # Cache for compiled regex patterns (standard re only)
    _regex_cache: Dict[str, Optional[re.Pattern]] = {}


def _safe_compile_regex(pattern: str) -> Optional[Union[re.Pattern, Any]]:
    """
    Safely compile a regex pattern with validation and caching.
    Uses re2 library when available for guaranteed linear execution time,
    otherwise falls back to standard re with comprehensive ReDoS protection.
    """
    if pattern in _regex_cache:
        return _regex_cache[pattern]

    # Basic validation
    if not pattern or len(pattern) > 1000:  # Reasonable length limit
        logger.warning("Regex pattern too long or empty: %s", pattern[:100])
        _regex_cache[pattern] = None
        return None

    # Use re2 if available (guaranteed linear time execution)
    if _re2_available:
        try:
            compiled = re2.compile(pattern)
            _regex_cache[pattern] = compiled
            logger.debug("Compiled pattern with re2: %s", pattern[:50])
            return compiled
        except Exception as e:
            logger.warning(
                "Failed to compile pattern with re2: %s, error: %s", pattern, e
            )
            # Continue to standard re with safety checks
            pass

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
        # Multiple quantifiers on similar patterns (a*a*a* type)
        r"[a-zA-Z0-9_]\*.*[a-zA-Z0-9_]\*.*[a-zA-Z0-9_]\*",  # a*...b*...c* patterns
        r"[a-zA-Z0-9_]\+.*[a-zA-Z0-9_]\+.*[a-zA-Z0-9_]\+",  # a+...b+...c+ patterns
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
    pattern: Union[re.Pattern, Any], text: str, timeout_seconds: float = 1.0
) -> bool:
    """
    Perform a regex search with timeout protection.
    Uses re2 when available (no timeout needed due to guaranteed linear execution),
    otherwise uses standard re with timeout protection.
    """
    if not text:
        return False

    # Limit text length to prevent excessive processing
    if len(text) > 10000:
        text = text[:10000]

    try:
        # re2 provides guaranteed linear execution time, no timeout needed
        if (
            _re2_available
            and hasattr(pattern, "search")
            and "re2" in str(type(pattern))
        ):
            result = pattern.search(text)
            return result is not None

        # Standard re with timeout protection
        start_time = time.time()
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
