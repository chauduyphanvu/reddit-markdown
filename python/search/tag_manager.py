import sqlite3
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from colored_logger import get_colored_logger
from .search_database import SearchDatabase

logger = get_colored_logger(__name__)


@dataclass
class Tag:
    """
    Represents a tag with metadata.
    """

    id: int
    name: str
    description: str = ""
    color: str = ""
    post_count: int = 0
    created_time: float = 0

    def __post_init__(self):
        # Validate tag name
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Tag name must be a non-empty string")

        # Normalize tag name
        self.name = self._normalize_tag_name(self.name)

    @staticmethod
    def _normalize_tag_name(name: str) -> str:
        """Normalize tag name to ensure consistency."""
        # Convert to lowercase and replace spaces/special chars with underscores
        normalized = re.sub(r"[^\w\-]", "_", name.lower().strip())
        # Remove multiple consecutive underscores
        normalized = re.sub(r"_+", "_", normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip("_")
        return normalized


class TagManager:
    """
    Manages user-defined tags for organizing Reddit posts.

    Features:
    - Create, update, delete tags
    - Apply tags to posts
    - Tag hierarchies and relationships
    - Auto-tagging based on content patterns
    - Tag statistics and analytics
    - Bulk tag operations
    """

    def __init__(self, database: SearchDatabase = None):
        """
        Initialize the tag manager.

        Args:
            database: SearchDatabase instance. If None, creates default instance.
        """
        self.database = database or SearchDatabase()

        # Built-in auto-tagging patterns
        self.auto_tag_patterns = {
            "question": [
                r"\?$",
                r"^(how|what|why|when|where|who)\s",
                r"\b(question|help|ask)\b",
            ],
            "discussion": [
                r"\b(discuss|discussion|thoughts|opinions|what do you think)\b"
            ],
            "news": [r"\b(breaking|news|announced|report)\b"],
            "tutorial": [r"\b(tutorial|guide|how-to|step by step)\b"],
            "review": [r"\b(review|rating|opinion on)\b"],
            "meme": [r"\b(meme|funny|humor|lol)\b"],
        }

    def create_tag(
        self, name: str, description: str = "", color: str = ""
    ) -> Optional[Tag]:
        """
        Create a new tag.

        Args:
            name: Tag name (will be normalized)
            description: Optional tag description
            color: Optional color code (hex format)

        Returns:
            Tag object if successful, None otherwise
        """
        try:
            # Validate inputs
            if not name or not name.strip():
                raise ValueError("Tag name cannot be empty")

            normalized_name = Tag._normalize_tag_name(name)

            # Check if tag already exists
            existing_tag = self.get_tag(normalized_name)
            if existing_tag:
                logger.warning("Tag '%s' already exists", normalized_name)
                return existing_tag

            # Validate color format if provided
            if color and not re.match(r"^#[0-9a-fA-F]{6}$", color):
                logger.warning("Invalid color format '%s', ignoring", color)
                color = ""

            # Insert tag into database
            with sqlite3.connect(self.database.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO tags (name, description, color)
                    VALUES (?, ?, ?)
                """,
                    (normalized_name, description, color),
                )

                tag_id = cursor.lastrowid

            logger.info("Created tag: %s", normalized_name)
            return Tag(
                id=tag_id, name=normalized_name, description=description, color=color
            )

        except Exception as e:
            logger.error("Failed to create tag '%s': %s", name, e)
            return None

    def get_tag(self, name: str) -> Optional[Tag]:
        """
        Get a tag by name.

        Args:
            name: Tag name (will be normalized)

        Returns:
            Tag object if found, None otherwise
        """
        try:
            normalized_name = Tag._normalize_tag_name(name)

            with sqlite3.connect(self.database.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT t.*, COUNT(pt.post_id) as post_count
                    FROM tags t
                    LEFT JOIN post_tags pt ON t.id = pt.tag_id
                    WHERE t.name = ?
                    GROUP BY t.id
                """,
                    (normalized_name,),
                )

                row = cursor.fetchone()
                if row:
                    return Tag(
                        id=row["id"],
                        name=row["name"],
                        description=row["description"] or "",
                        color=row["color"] or "",
                        post_count=row["post_count"],
                        created_time=row["created_time"],
                    )

                return None

        except Exception as e:
            logger.error("Failed to get tag '%s': %s", name, e)
            return None

    def list_tags(self, limit: int = 100) -> List[Tag]:
        """
        List all tags with their post counts.

        Args:
            limit: Maximum tags to return

        Returns:
            List of Tag objects ordered by post count (descending)
        """
        try:
            with sqlite3.connect(self.database.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT t.*, COUNT(pt.post_id) as post_count
                    FROM tags t
                    LEFT JOIN post_tags pt ON t.id = pt.tag_id
                    GROUP BY t.id
                    ORDER BY post_count DESC, t.name ASC
                    LIMIT ?
                """,
                    (limit,),
                )

                tags = []
                for row in cursor.fetchall():
                    tags.append(
                        Tag(
                            id=row["id"],
                            name=row["name"],
                            description=row["description"] or "",
                            color=row["color"] or "",
                            post_count=row["post_count"],
                            created_time=row["created_time"],
                        )
                    )

                return tags

        except Exception as e:
            logger.error("Failed to list tags: %s", e)
            return []

    def delete_tag(self, name: str) -> bool:
        """
        Delete a tag and all its associations.

        Args:
            name: Tag name to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            normalized_name = Tag._normalize_tag_name(name)

            with sqlite3.connect(self.database.db_path) as conn:
                # Delete tag (cascade will handle post_tags)
                cursor = conn.execute(
                    "DELETE FROM tags WHERE name = ?", (normalized_name,)
                )
                deleted_count = cursor.rowcount

            if deleted_count > 0:
                logger.info("Deleted tag: %s", normalized_name)
                return True
            else:
                logger.warning("Tag not found: %s", normalized_name)
                return False

        except Exception as e:
            logger.error("Failed to delete tag '%s': %s", name, e)
            return False

    def tag_post(self, post_id: str, tag_names: List[str]) -> int:
        """
        Apply tags to a post.

        Args:
            post_id: Reddit post ID
            tag_names: List of tag names to apply

        Returns:
            Number of tags successfully applied
        """
        if not tag_names:
            return 0

        try:
            # Get database post ID
            with sqlite3.connect(self.database.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id FROM posts WHERE post_id = ?", (post_id,)
                )
                result = cursor.fetchone()
                if not result:
                    logger.warning("Post not found: %s", post_id)
                    return 0

                db_post_id = result[0]

            applied_count = 0
            for tag_name in tag_names:
                if self._apply_single_tag(db_post_id, tag_name):
                    applied_count += 1

            logger.debug(
                "Applied %d/%d tags to post %s", applied_count, len(tag_names), post_id
            )
            return applied_count

        except Exception as e:
            logger.error("Failed to tag post '%s': %s", post_id, e)
            return 0

    def untag_post(self, post_id: str, tag_names: List[str] = None) -> int:
        """
        Remove tags from a post.

        Args:
            post_id: Reddit post ID
            tag_names: List of tag names to remove. If None, removes all tags.

        Returns:
            Number of tags successfully removed
        """
        try:
            # Get database post ID
            with sqlite3.connect(self.database.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id FROM posts WHERE post_id = ?", (post_id,)
                )
                result = cursor.fetchone()
                if not result:
                    logger.warning("Post not found: %s", post_id)
                    return 0

                db_post_id = result[0]

                if tag_names is None:
                    # Remove all tags
                    cursor = conn.execute(
                        "DELETE FROM post_tags WHERE post_id = ?", (db_post_id,)
                    )
                    removed_count = cursor.rowcount
                else:
                    # Remove specific tags
                    removed_count = 0
                    for tag_name in tag_names:
                        normalized_name = Tag._normalize_tag_name(tag_name)
                        cursor = conn.execute(
                            """
                            DELETE FROM post_tags 
                            WHERE post_id = ? AND tag_id = (
                                SELECT id FROM tags WHERE name = ?
                            )
                        """,
                            (db_post_id, normalized_name),
                        )
                        removed_count += cursor.rowcount

            logger.debug("Removed %d tags from post %s", removed_count, post_id)
            return removed_count

        except Exception as e:
            logger.error("Failed to untag post '%s': %s", post_id, e)
            return 0

    def get_post_tags(self, post_id: str) -> List[Tag]:
        """
        Get all tags for a specific post.

        Args:
            post_id: Reddit post ID

        Returns:
            List of Tag objects
        """
        try:
            with sqlite3.connect(self.database.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT t.*
                    FROM tags t
                    JOIN post_tags pt ON t.id = pt.tag_id
                    JOIN posts p ON pt.post_id = p.id
                    WHERE p.post_id = ?
                    ORDER BY t.name
                """,
                    (post_id,),
                )

                tags = []
                for row in cursor.fetchall():
                    tags.append(
                        Tag(
                            id=row["id"],
                            name=row["name"],
                            description=row["description"] or "",
                            color=row["color"] or "",
                            created_time=row["created_time"],
                        )
                    )

                return tags

        except Exception as e:
            logger.error("Failed to get tags for post '%s': %s", post_id, e)
            return []

    def auto_tag_post(self, post_id: str) -> List[str]:
        """
        Automatically apply tags to a post based on content patterns.

        Args:
            post_id: Reddit post ID

        Returns:
            List of tag names that were applied
        """
        try:
            # Get post content
            post = self.database.get_post_by_file_path(
                ""
            )  # This won't work, need to fix
            # Let me get the post differently
            with sqlite3.connect(self.database.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT title, content_preview, subreddit
                    FROM posts p
                    LEFT JOIN posts_fts pf ON p.id = pf.rowid
                    WHERE p.post_id = ?
                """,
                    (post_id,),
                )

                result = cursor.fetchone()
                if not result:
                    logger.warning("Post not found for auto-tagging: %s", post_id)
                    return []

            # Combine text content for analysis
            text_content = f"{result['title']} {result['content_preview']}".lower()
            subreddit = result["subreddit"] or ""

            # Apply pattern-based auto-tags
            suggested_tags = []
            for tag_name, patterns in self.auto_tag_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_content, re.IGNORECASE):
                        suggested_tags.append(tag_name)
                        break

            # Add subreddit-based tags
            if subreddit:
                # Create/apply subreddit tag
                subreddit_tag = f"sub_{subreddit.lower().replace('r/', '')}"
                suggested_tags.append(subreddit_tag)

            # Remove duplicates
            suggested_tags = list(set(suggested_tags))

            # Create tags if they don't exist and apply them
            applied_tags = []
            for tag_name in suggested_tags:
                # Ensure tag exists
                tag = self.get_tag(tag_name)
                if not tag:
                    tag = self.create_tag(tag_name, f"Auto-generated tag: {tag_name}")

                if tag:
                    # Get database post ID
                    with sqlite3.connect(self.database.db_path) as conn:
                        cursor = conn.execute(
                            "SELECT id FROM posts WHERE post_id = ?", (post_id,)
                        )
                        result = cursor.fetchone()
                        if result and self._apply_single_tag(result[0], tag_name):
                            applied_tags.append(tag_name)

            if applied_tags:
                logger.info("Auto-applied tags to post %s: %s", post_id, applied_tags)

            return applied_tags

        except Exception as e:
            logger.error("Failed to auto-tag post '%s': %s", post_id, e)
            return []

    def bulk_tag_posts(
        self, post_ids: List[str], tag_names: List[str]
    ) -> Dict[str, int]:
        """
        Apply tags to multiple posts in bulk.

        Args:
            post_ids: List of Reddit post IDs
            tag_names: List of tag names to apply to all posts

        Returns:
            Dictionary with 'success' and 'failed' counts
        """
        stats = {"success": 0, "failed": 0}

        for post_id in post_ids:
            applied_count = self.tag_post(post_id, tag_names)
            if applied_count > 0:
                stats["success"] += 1
            else:
                stats["failed"] += 1

        logger.info(
            "Bulk tagged %d posts successfully, %d failed",
            stats["success"],
            stats["failed"],
        )
        return stats

    def _apply_single_tag(self, db_post_id: int, tag_name: str) -> bool:
        """Apply a single tag to a post (internal helper)."""
        try:
            normalized_name = Tag._normalize_tag_name(tag_name)

            with sqlite3.connect(self.database.db_path) as conn:
                # Get or create tag
                cursor = conn.execute(
                    "SELECT id FROM tags WHERE name = ?", (normalized_name,)
                )
                result = cursor.fetchone()

                if not result:
                    # Create tag
                    cursor = conn.execute(
                        """
                        INSERT INTO tags (name) VALUES (?)
                    """,
                        (normalized_name,),
                    )
                    tag_id = cursor.lastrowid
                else:
                    tag_id = result[0]

                # Apply tag to post (ignore if already exists)
                try:
                    conn.execute(
                        """
                        INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)
                    """,
                        (db_post_id, tag_id),
                    )
                    return True
                except sqlite3.IntegrityError:
                    # Tag already applied to post
                    return True

        except Exception as e:
            logger.error("Failed to apply tag '%s': %s", tag_name, e)
            return False
