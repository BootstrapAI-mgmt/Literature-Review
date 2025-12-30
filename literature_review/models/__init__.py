"""
Literature Review Models Package

This package contains data models for the operationalization features:
- ActionVector: Executable steps from research
- ValidationStrategy: Requirement validation definitions
"""

from literature_review.models.action_vector import (
    ActionVector,
    ActionType,
    EffortLevel,
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

__all__ = [
    # Action Vector
    "ActionVector",
    "ActionType", 
    "EffortLevel",
    "ResourceRequirements",
    "ReproducibilityInfo",
    "ActionChainPosition",
    "generate_action_id",
    
    # Validation Strategy
    "ValidationStrategy",
    "ValidationStatus",
    "EvidenceType",
    "BenchmarkLink",
    "MetricDefinition"
]
