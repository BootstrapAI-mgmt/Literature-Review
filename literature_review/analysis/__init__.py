"""
Analysis package for literature review.

This package contains modules for analyzing and judging research claims.
"""

# Lazy imports to avoid loading all dependencies at import time
__all__ = [
    "assess_actionability",
    "enhanced_judge_claim",
    "ACTIONABILITY_PROMPT"
]

def __getattr__(name):
    """Lazy import to avoid loading all dependencies at import time."""
    if name in __all__:
        from literature_review.analysis.judge import (
            assess_actionability,
            enhanced_judge_claim,
            ACTIONABILITY_PROMPT
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
