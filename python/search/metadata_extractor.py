import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


class MetadataExtractor:
    """
    Extracts metadata and content from Reddit markdown files for indexing.

    Parses the structured markdown format created by the post_renderer
    to extract post metadata, content, and reply information.
    """

    def __init__(self):
        """Initialize the metadata extractor."""
        # Regex patterns for parsing markdown structure
        self.patterns = {
            "subreddit_author": re.compile(
                r"\*\*(.+?)\*\*\s*\|\s*Posted by u/(.+?)(?:\s|$)"
            ),
            "title": re.compile(r"^## (.+)$", re.MULTILINE),
            "original_url": re.compile(r"Original post: \[(.+?)\]\((.+?)\)"),
            "upvotes": re.compile(r"⬆️\s*(\d+(?:\.\d+)?k?)"),
            "timestamp": re.compile(
                r"_\(\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\)_"
            ),
            "reply_count": re.compile(r"💬 ~ (\d+) replies"),
            "post_id_from_url": re.compile(r"/comments/([a-z0-9]+)/"),
        }

    def extract_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from a Reddit markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Dictionary containing extracted metadata and content, or None if extraction fails
        """
        if not os.path.exists(file_path):
            logger.warning("File does not exist: %s", file_path)
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                logger.warning("Empty file: %s", file_path)
                return None

            # Extract file metadata
            file_stat = os.stat(file_path)

            # Extract post metadata from content
            metadata = self._parse_content(content)
            if not metadata:
                logger.warning("Could not parse metadata from %s", file_path)
                return None

            # Add file information
            metadata.update(
                {
                    "file_path": file_path,
                    "content": content,
                    "file_size": file_stat.st_size,
                    "file_modified_time": file_stat.st_mtime,
                    "content_preview": self._generate_preview(content),
                }
            )

            # Extract post ID from filename or URL
            if "post_id" not in metadata:
                metadata["post_id"] = self._extract_post_id(file_path, content)

            logger.debug("Extracted metadata from %s", file_path)
            return metadata

        except Exception as e:
            logger.error("Failed to extract metadata from %s: %s", file_path, e)
            return None

    def _parse_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse post content to extract structured metadata."""
        metadata = {}

        try:
            # Extract subreddit and author from first line
            subreddit_match = self.patterns["subreddit_author"].search(content)
            if subreddit_match:
                metadata["subreddit"] = subreddit_match.group(1).strip()
                author_part = subreddit_match.group(2).strip()

                # Remove upvotes and timestamp from author part
                author_clean = re.sub(r"⬆️.*$", "", author_part).strip()
                metadata["author"] = author_clean

            # Extract title
            title_match = self.patterns["title"].search(content)
            if title_match:
                metadata["title"] = title_match.group(1).strip()

            # Extract original URL
            url_match = self.patterns["original_url"].search(content)
            if url_match:
                metadata["url"] = url_match.group(2).strip()

            # Extract upvotes
            upvotes_match = self.patterns["upvotes"].search(content)
            if upvotes_match:
                upvote_str = upvotes_match.group(1)
                metadata["upvotes"] = self._parse_upvote_count(upvote_str)

            # Extract timestamp
            timestamp_match = self.patterns["timestamp"].search(content)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                metadata["created_utc"] = self._parse_timestamp(timestamp_str)

            # Extract reply count
            reply_match = self.patterns["reply_count"].search(content)
            if reply_match:
                metadata["reply_count"] = int(reply_match.group(1))

            # Ensure we have at least a title
            if "title" not in metadata:
                logger.warning("No title found in content")
                return None

            return metadata

        except Exception as e:
            logger.error("Failed to parse content: %s", e)
            return None

    def _extract_post_id(self, file_path: str, content: str) -> str:
        """Extract Reddit post ID from filename or URL in content."""
        # First try to extract from URL in content
        url_match = self.patterns["original_url"].search(content)
        if url_match:
            url = url_match.group(2)
            post_id_match = self.patterns["post_id_from_url"].search(url)
            if post_id_match:
                return post_id_match.group(1)

        # Fall back to filename parsing
        filename = Path(file_path).stem

        # Remove subreddit prefix if present (e.g., "r_Python_abc123" -> "abc123")
        if "_" in filename:
            parts = filename.split("_")
            # Look for Reddit post ID pattern (alphanumeric, usually 6-7 chars)
            for part in reversed(parts):
                if re.match(r"^[a-z0-9]{6,8}$", part):
                    return part

        # Last resort: use filename without extension
        return filename

    def _parse_upvote_count(self, upvote_str: str) -> int:
        """Parse upvote string (e.g., '1.2k', '150') to integer."""
        upvote_str = upvote_str.lower().strip()

        if upvote_str.endswith("k"):
            try:
                base_value = float(upvote_str[:-1])
                return int(base_value * 1000)
            except ValueError:
                return 0
        else:
            try:
                return int(upvote_str)
            except ValueError:
                return 0

    def _parse_timestamp(self, timestamp_str: str) -> int:
        """Parse timestamp string to Unix epoch."""
        try:
            from datetime import datetime, timezone

            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            # Assume UTC
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            logger.warning("Could not parse timestamp: %s", timestamp_str)
            return 0

    def _generate_preview(self, content: str, max_length: int = 200) -> str:
        """Generate a preview of the post content."""
        # Remove markdown formatting for preview
        clean_content = self._strip_markdown(content)

        # Find the start of actual post content (after metadata lines)
        lines = clean_content.split("\n")
        content_lines = []

        # Skip header lines (subreddit, title, url, etc.)
        skip_patterns = [
            r"^\*\*.*\*\*.*Posted by",  # Header line
            r"^##\s",  # Title line
            r"^Original post:",  # URL line
            r"^💬 ~.*replies",  # Reply count
            r"^---+$",  # Separator
            r"^\s*$",  # Empty lines
        ]

        found_content = False
        for line in lines:
            line = line.strip()
            if not line:
                if found_content:
                    break  # Stop at first empty line after content starts
                continue

            # Check if this is a metadata line to skip
            is_metadata = any(re.match(pattern, line) for pattern in skip_patterns)
            if is_metadata and not found_content:
                continue

            # This is content
            found_content = True
            content_lines.append(line)

            # Stop if we have enough content
            if len(" ".join(content_lines)) >= max_length:
                break

        preview = " ".join(content_lines)
        if len(preview) > max_length:
            preview = preview[:max_length].rsplit(" ", 1)[0] + "..."

        return preview or "No preview available"

    def _strip_markdown(self, text: str) -> str:
        """Remove basic markdown formatting for cleaner text processing."""
        # Remove links: [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        # Remove bold/italic: **text** or *text* -> text
        text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)

        # Remove code blocks: `code` -> code
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove blockquote markers
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def is_reddit_markdown_file(self, file_path: str) -> bool:
        """
        Check if a file is a Reddit markdown file based on content structure.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file appears to be a Reddit markdown file
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Read only first few lines for efficiency
                first_lines = []
                for i, line in enumerate(f):
                    first_lines.append(line)
                    if i >= 10:  # Check first 10 lines
                        break

                content_sample = "".join(first_lines)

            # Check for Reddit-specific patterns
            reddit_indicators = [
                r"\*\*r/.*\*\*.*Posted by u/",  # Subreddit and author line
                r"Original post: \[.*\]\(.*reddit\.com.*\)",  # Reddit URL
                r"💬 ~ \d+ replies",  # Reply count
            ]

            matches = sum(
                1 for pattern in reddit_indicators if re.search(pattern, content_sample)
            )

            # Need at least 2 indicators to be confident
            return matches >= 2

        except UnicodeDecodeError as e:
            logger.debug("File %s has encoding issues: %s", file_path, e)
            # Re-raise so caller can distinguish between corrupted and non-Reddit files
            raise
        except Exception as e:
            logger.debug("Could not check file %s: %s", file_path, e)
            return False
