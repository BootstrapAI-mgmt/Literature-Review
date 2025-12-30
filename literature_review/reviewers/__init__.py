"""
Reviewers package for literature review.

This package contains modules for reviewing and analyzing research papers.
"""

# Lazy imports to avoid importing heavy dependencies unless needed
__all__ = [
    "extract_operationalization",
    "run_operationalization_extraction"
]

def __getattr__(name):
    """Lazy import to avoid loading all dependencies at import time."""
    if name in __all__:
        from literature_review.reviewers.deep_reviewer import (
            extract_operationalization,
            run_operationalization_extraction
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
