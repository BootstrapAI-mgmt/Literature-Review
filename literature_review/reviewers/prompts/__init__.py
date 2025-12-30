"""
Prompts Package for Literature Review.

This package contains prompt templates and formatting functions
for various extraction tasks.
"""

from literature_review.reviewers.prompts.benchmark_prompt import (
    BENCHMARK_EXTRACTION_PROMPT,
    format_benchmark_extraction_prompt,
    get_pillar_metrics
)

__all__ = [
    "BENCHMARK_EXTRACTION_PROMPT",
    "format_benchmark_extraction_prompt",
    "get_pillar_metrics"
]
