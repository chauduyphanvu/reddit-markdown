"""
Reddit-Markdown Search Module

Provides full-text search, content indexing, and tag-based organization 
for downloaded Reddit posts.

Key Components:
- SearchDatabase: SQLite-based search index storage
- MetadataExtractor: Extracts metadata from markdown files  
- ContentIndexer: Indexes posts and builds search database
- SearchEngine: Full-text search with filtering and ranking
- TagManager: User-defined tag system with hierarchical organization
"""

from .search_database import SearchDatabase
from .metadata_extractor import MetadataExtractor
from .indexer import ContentIndexer
from .search_engine import SearchEngine, SearchQuery, SearchResult
from .tag_manager import TagManager, Tag

__all__ = [
    "SearchDatabase",
    "MetadataExtractor",
    "ContentIndexer",
    "SearchEngine",
    "SearchQuery",
    "SearchResult",
    "TagManager",
    "Tag",
]
