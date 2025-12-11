"""
Literature Review Configuration Module

Provides centralized configuration management for research domain settings.
"""

from literature_review.config.research_config import (
    ResearchConfig,
    load_config,
    get_config,
    reset_config,
)

__all__ = [
    "ResearchConfig",
    "load_config",
    "get_config",
    "reset_config",
]
