"""
Literature Review Models Package

This package contains data models for the operationalization features:
- ActionVector: Executable steps from research
- ValidationStrategy: Requirement validation definitions
- DomainStakeholder: Stakeholder types from literature
- LiteratureStakeholderImpact: Gap-stakeholder relationships
"""

from literature_review.models.action_vector import (
    ActionVector,
    ActionType,
    EffortLevel,
    ComputeScale,
    ResourceRequirements,
    ReproducibilityInfo,
    ActionChainPosition,
    generate_action_id
)

from literature_review.models.validation_strategy import (
    ValidationStrategy,
    ValidationStatus,
    EvidenceType,
    BenchmarkLink,
    MetricDefinition
)

from literature_review.models.domain_stakeholder import (
    DomainStakeholder,
    LiteratureStakeholderImpact,
    StakeholderCategory,
    generate_impact_id
)

__all__ = [
    # Action Vector
    "ActionVector",
    "ActionType", 
    "EffortLevel",
    "ComputeScale",
    "ResourceRequirements",
    "ReproducibilityInfo",
    "ActionChainPosition",
    "generate_action_id",
    
    # Validation Strategy
    "ValidationStrategy",
    "ValidationStatus",
    "EvidenceType",
    "BenchmarkLink",
    "MetricDefinition",
    
    # Domain Stakeholder
    "DomainStakeholder",
    "LiteratureStakeholderImpact",
    "StakeholderCategory",
    "generate_impact_id"
]
