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

from literature_review.reviewers.prompts.operationalization_prompt import (
    OPERATIONALIZATION_EXTRACTION_PROMPT,
    BATCH_OPERATIONALIZATION_PROMPT,
    BATCH_EVIDENCE_TRUNCATION_LIMIT,
    format_claim_for_prompt,
    format_claims_batch
)

from literature_review.reviewers.prompts.stakeholder_extraction_prompt import (
    STAKEHOLDER_IMPACT_EXTRACTION_PROMPT,
    STAKEHOLDER_IMPACT_BATCH_PROMPT,
    MIN_CONFIDENCE_THRESHOLD,
    MAX_IMPACTS_PER_PAPER,
    format_stakeholder_extraction_prompt,
    format_stakeholder_batch_prompt,
    parse_extraction_response
)

__all__ = [
    # Benchmark prompts (from PR #99)
    "BENCHMARK_EXTRACTION_PROMPT",
    "format_benchmark_extraction_prompt",
    "get_pillar_metrics",
    # Operationalization prompts (from PR #98)
    "OPERATIONALIZATION_EXTRACTION_PROMPT",
    "BATCH_OPERATIONALIZATION_PROMPT",
    "BATCH_EVIDENCE_TRUNCATION_LIMIT",
    "format_claim_for_prompt",
    "format_claims_batch",
    # Stakeholder extraction prompts
    "STAKEHOLDER_IMPACT_EXTRACTION_PROMPT",
    "STAKEHOLDER_IMPACT_BATCH_PROMPT",
    "MIN_CONFIDENCE_THRESHOLD",
    "MAX_IMPACTS_PER_PAPER",
    "format_stakeholder_extraction_prompt",
    "format_stakeholder_batch_prompt",
    "parse_extraction_response"
]
