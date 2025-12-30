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

from literature_review.analysis.action_generator import (
    ActionGenerator,
    ActionChain,
    GeneratedAction,
    ActionStatus,
    ActionPriority,
    generate_action_vectors
)

from literature_review.analysis.pillar_evolution import (
    PillarEvolutionManager,
    ModificationProposal,
    ProposalStatus,
    ModificationType,
    EvidenceReference,
    ImpactAssessment,
    ReviewComment
)

from literature_review.analysis.domain_stakeholder_extractor import (
    DomainStakeholderExtractor
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
    "ActionGenerator",
    "ActionChain",
    "GeneratedAction",
    "ActionStatus",
    "ActionPriority",
    "generate_action_vectors",
    "PillarEvolutionManager",
    "ModificationProposal",
    "ProposalStatus",
    "ModificationType",
    "EvidenceReference",
    "ImpactAssessment",
    "ReviewComment",
    "DomainStakeholderExtractor",
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
