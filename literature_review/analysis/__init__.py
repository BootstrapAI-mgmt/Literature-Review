"""
Analysis Package for Literature Review.

This package contains analysis modules for processing and
analyzing research literature.
"""

from literature_review.analysis.benchmark_analyzer import (
    BenchmarkAnalyzer,
    BenchmarkCoverage,
    generate_benchmark_matrix
)

# Lazy imports for judge functions to avoid loading all dependencies at import time
_lazy_exports = [
    "assess_actionability",
    "enhanced_judge_claim",
    "ACTIONABILITY_PROMPT"
]

__all__ = [
    "BenchmarkAnalyzer",
    "BenchmarkCoverage",
    "generate_benchmark_matrix",
    "assess_actionability",
    "enhanced_judge_claim",
    "ACTIONABILITY_PROMPT"
]

def __getattr__(name):
    """Lazy import to avoid loading all dependencies at import time."""
    if name in _lazy_exports:
        from literature_review.analysis.judge import (
            assess_actionability,
            enhanced_judge_claim,
            ACTIONABILITY_PROMPT
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
