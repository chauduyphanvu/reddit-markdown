"""
CI/CD Runner for Reddit-Markdown
===========================================

A local-first CI/CD system with minimal dependencies and maximum simplicity.
"""

__version__ = "1.0.0"
__author__ = "Reddit-Markdown CI System"

from .runner import CIRunner
from .config import load_config

__all__ = ["CIRunner", "load_config"]
