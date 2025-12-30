"""
Prompt templates for reviewers.

This package contains prompt templates used by various reviewer modules
for extracting and analyzing research paper content.
"""

from literature_review.reviewers.prompts.operationalization_prompt import (
    OPERATIONALIZATION_EXTRACTION_PROMPT,
    BATCH_OPERATIONALIZATION_PROMPT,
    format_claim_for_prompt,
    format_claims_batch
)

__all__ = [
    "OPERATIONALIZATION_EXTRACTION_PROMPT",
    "BATCH_OPERATIONALIZATION_PROMPT",
    "format_claim_for_prompt",
    "format_claims_batch"
]
