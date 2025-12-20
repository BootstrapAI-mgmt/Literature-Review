# Task Card: Action Vector Generator

**Task ID:** OP-W3-2  
**Wave:** 3 (Analysis & Output)  
**Priority:** HIGH  
**Estimated Effort:** 10 hours  
**Status:** Not Started  
**Dependencies:** OP-W1-1 (Schema Foundation), OP-W2-1 (Action Extraction)  
**Blocks:** None (final output module)

---

## Objective

Generate structured action vectors from approved claims and operationalization metadata. Create implementation-ready action chains with dependencies, resource requirements, and reproducibility assessments. Output `action_vectors.json` for research-to-development handoff.

## Background

After the deep reviewer extracts operationalization metadata and the judge approves claims, we need to:

1. **Synthesize actions**: Combine claims into implementation steps
2. **Build action chains**: Order actions by dependencies
3. **Assess reproducibility**: Score each action's reproducibility
4. **Generate vectors**: Produce structured, executable action items

This is the final operationalization step that transforms research findings into development tasks.

## Success Criteria

- [ ] `action_generator.py` module created
- [ ] Action vectors generated from approved claims
- [ ] Chain dependencies correctly computed
- [ ] Reproducibility scores based on paper metadata
- [ ] Resource requirements estimated
- [ ] `action_vectors.json` output generated
- [ ] Unit tests with >90% coverage

---

## Deliverables

### 1. Action Generator Module

**File:** `literature_review/analysis/action_generator.py`

```python
"""
Action Vector Generator

Generates structured action vectors from approved claims
and operationalization metadata extracted during deep review.
"""

import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from enum import Enum

from literature_review.models import (
    ActionVector,
    ReproducibilityInfo,
    ResourceRequirements,
    ActionChainPosition,
    ComputeScale
)

logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    """Status of an action in implementation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class ActionPriority(Enum):
    """Priority levels for actions."""
    CRITICAL = "critical"       # Must complete for system viability
    HIGH = "high"               # Important for core functionality
    MEDIUM = "medium"           # Valuable but not blocking
    LOW = "low"                 # Nice to have
    OPTIONAL = "optional"       # Can skip if resources limited


@dataclass
class GeneratedAction:
    """
    A generated action with full context.
    
    Extends ActionVector with generation metadata.
    """
    # Core vector
    action_vector: ActionVector
    
    # Generation metadata
    generation_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Source tracking
    source_claims: List[str] = field(default_factory=list)
    source_papers: List[str] = field(default_factory=list)
    pillar_mappings: List[str] = field(default_factory=list)
    
    # Priority and status
    priority: ActionPriority = ActionPriority.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    
    # Dependencies (other action IDs)
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    
    # Effort estimation
    estimated_hours: float = 0.0
    complexity_score: float = 0.5  # 0-1, higher = more complex
    
    def to_dict(self) -> Dict:
        """Convert to serializable dictionary."""
        return {
            "action_vector": asdict(self.action_vector),
            "generation_id": self.generation_id,
            "generated_at": self.generated_at,
            "source_claims": self.source_claims,
            "source_papers": self.source_papers,
            "pillar_mappings": self.pillar_mappings,
            "priority": self.priority.value,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "blocks": self.blocks,
            "estimated_hours": self.estimated_hours,
            "complexity_score": self.complexity_score
        }


@dataclass
class ActionChain:
    """
    A chain of related actions.
    
    Represents a sequence of actions that together address
    a requirement or capability.
    """
    chain_id: str
    name: str
    description: str
    
    actions: List[GeneratedAction] = field(default_factory=list)
    
    # Target pillar/requirement
    target_pillar: str = ""
    target_requirement: str = ""
    
    # Chain metrics
    total_actions: int = 0
    completed_actions: int = 0
    blocked_actions: int = 0
    
    # Estimated totals
    total_hours: float = 0.0
    critical_path_hours: float = 0.0
    
    def calculate_metrics(self):
        """Calculate chain metrics from actions."""
        self.total_actions = len(self.actions)
        self.completed_actions = sum(
            1 for a in self.actions 
            if a.status == ActionStatus.COMPLETED
        )
        self.blocked_actions = sum(
            1 for a in self.actions 
            if a.status == ActionStatus.BLOCKED
        )
        self.total_hours = sum(a.estimated_hours for a in self.actions)
        
        # Critical path: sum of sequential dependencies
        self.critical_path_hours = self._calculate_critical_path()
    
    def _calculate_critical_path(self) -> float:
        """Calculate critical path duration."""
        if not self.actions:
            return 0.0
        
        # Simple: find longest path through dependencies
        action_map = {a.generation_id: a for a in self.actions}
        
        def get_path_length(action_id: str, visited: Set[str]) -> float:
            if action_id in visited or action_id not in action_map:
                return 0.0
            
            visited.add(action_id)
            action = action_map[action_id]
            
            max_dep_length = 0.0
            for dep_id in action.depends_on:
                dep_length = get_path_length(dep_id, visited.copy())
                max_dep_length = max(max_dep_length, dep_length)
            
            return action.estimated_hours + max_dep_length
        
        # Find action with no dependents (end of chains)
        all_deps = set()
        for a in self.actions:
            all_deps.update(a.depends_on)
        
        end_actions = [
            a.generation_id for a in self.actions 
            if a.generation_id not in all_deps
        ]
        
        if not end_actions:
            end_actions = [self.actions[-1].generation_id]
        
        return max(
            get_path_length(action_id, set()) 
            for action_id in end_actions
        )
    
    def to_dict(self) -> Dict:
        """Convert to serializable dictionary."""
        self.calculate_metrics()
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "target_pillar": self.target_pillar,
            "target_requirement": self.target_requirement,
            "total_actions": self.total_actions,
            "completed_actions": self.completed_actions,
            "blocked_actions": self.blocked_actions,
            "total_hours": self.total_hours,
            "critical_path_hours": self.critical_path_hours,
            "completion_percentage": round(
                self.completed_actions / self.total_actions * 100, 1
            ) if self.total_actions > 0 else 0
        }


class ActionGenerator:
    """
    Generate action vectors from approved claims.
    
    Processes:
    1. Judge-approved claims
    2. Operationalization metadata from deep review
    3. Pillar definitions for context
    
    Outputs:
    - Structured action vectors
    - Action chains with dependencies
    - Resource and reproducibility assessments
    """
    
    def __init__(
        self,
        pillar_definitions_path: str,
        version_history_path: Optional[str] = None
    ):
        """
        Initialize action generator.
        
        Args:
            pillar_definitions_path: Path to pillar definitions
            version_history_path: Optional path to version history
        """
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        self.version_history = {}
        if version_history_path and Path(version_history_path).exists():
            with open(version_history_path, 'r', encoding='utf-8') as f:
                self.version_history = json.load(f)
        
        # Generated output
        self.actions: List[GeneratedAction] = []
        self.chains: List[ActionChain] = []
    
    def generate_actions(
        self,
        approved_claims: List[Dict],
        operationalization_data: Optional[Dict] = None
    ) -> Dict:
        """
        Generate action vectors from approved claims.
        
        Args:
            approved_claims: List of judge-approved claims
            operationalization_data: Optional operationalization metadata
        
        Returns:
            Complete action generation output
        """
        logger.info(f"Generating actions from {len(approved_claims)} claims")
        
        # Group claims by pillar/requirement
        grouped = self._group_claims(approved_claims)
        
        # Generate actions for each group
        for key, claims in grouped.items():
            pillar, requirement = key
            
            chain = self._generate_action_chain(
                pillar=pillar,
                requirement=requirement,
                claims=claims,
                operationalization=operationalization_data
            )
            
            self.chains.append(chain)
            self.actions.extend(chain.actions)
        
        # Resolve cross-chain dependencies
        self._resolve_dependencies()
        
        # Calculate priorities
        self._calculate_priorities()
        
        return self._generate_output()
    
    def _group_claims(self, claims: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
        """Group claims by pillar and requirement."""
        grouped = defaultdict(list)
        
        for claim in claims:
            pillar = claim.get("pillar", "Unknown")
            requirement = claim.get("requirement", "General")
            
            grouped[(pillar, requirement)].append(claim)
        
        return grouped
    
    def _generate_action_chain(
        self,
        pillar: str,
        requirement: str,
        claims: List[Dict],
        operationalization: Optional[Dict] = None
    ) -> ActionChain:
        """Generate an action chain for a set of claims."""
        
        # Create chain identifier
        chain_id = self._generate_id(f"{pillar}::{requirement}")
        
        chain = ActionChain(
            chain_id=chain_id,
            name=f"Actions for {requirement}",
            description=f"Implementation actions derived from {len(claims)} approved claims",
            target_pillar=pillar,
            target_requirement=requirement
        )
        
        # Sort claims by potential ordering hints
        sorted_claims = self._sort_claims_by_dependency(claims)
        
        previous_action_id = None
        
        for i, claim in enumerate(sorted_claims):
            action = self._claim_to_action(
                claim=claim,
                chain_id=chain_id,
                position=i,
                total=len(sorted_claims),
                previous_action_id=previous_action_id,
                operationalization=operationalization
            )
            
            chain.actions.append(action)
            previous_action_id = action.generation_id
        
        return chain
    
    def _claim_to_action(
        self,
        claim: Dict,
        chain_id: str,
        position: int,
        total: int,
        previous_action_id: Optional[str],
        operationalization: Optional[Dict] = None
    ) -> GeneratedAction:
        """Convert a single claim to an action."""
        
        # Generate action ID
        action_id = self._generate_id(f"{chain_id}::action_{position}")
        
        # Extract paper info
        paper_id = claim.get("paper_id", claim.get("source_paper", "unknown"))
        claim_text = claim.get("claim_text", claim.get("claim", ""))
        
        # Get operationalization data if available
        op_data = {}
        if operationalization and paper_id in operationalization:
            op_data = operationalization[paper_id]
        
        # Create reproducibility info
        reproducibility = self._assess_reproducibility(claim, op_data)
        
        # Create resource requirements
        resources = self._estimate_resources(claim, op_data)
        
        # Create chain position
        chain_position = ActionChainPosition(
            chain_id=chain_id,
            position_in_chain=position,
            total_chain_length=total,
            is_first=position == 0,
            is_last=position == total - 1,
            predecessor_id=previous_action_id,
            successor_id=None  # Will be set later
        )
        
        # Create the core action vector
        action_vector = ActionVector(
            action_id=action_id,
            description=self._generate_action_description(claim_text),
            source_paper_id=paper_id,
            source_claim=claim_text,
            reproducibility=reproducibility,
            resources=resources,
            chain_position=chain_position,
            validation_requirements=claim.get("validation_requirements", []),
            target_requirement_ids=claim.get("requirement_mappings", [])
        )
        
        # Create generated action with metadata
        generated_action = GeneratedAction(
            action_vector=action_vector,
            generation_id=action_id,
            source_claims=[claim.get("claim_id", claim_text[:50])],
            source_papers=[paper_id],
            pillar_mappings=claim.get("requirement_mappings", []),
            depends_on=[previous_action_id] if previous_action_id else [],
            estimated_hours=self._estimate_hours(claim, op_data),
            complexity_score=self._calculate_complexity(claim, op_data)
        )
        
        return generated_action
    
    def _assess_reproducibility(
        self,
        claim: Dict,
        op_data: Dict
    ) -> ReproducibilityInfo:
        """Assess reproducibility of a claim/action."""
        
        # Check for code/data availability
        has_code = op_data.get("code_available", False) or "github" in claim.get("claim_text", "").lower()
        has_data = op_data.get("data_available", False)
        
        # Get hardware info from operationalization
        hardware = op_data.get("hardware_requirements", [])
        if not hardware and "GPU" in claim.get("claim_text", ""):
            hardware = ["GPU"]
        
        # Estimate reproducibility score
        score = 0.5  # Base score
        if has_code:
            score += 0.2
        if has_data:
            score += 0.15
        if hardware:
            score += 0.1
        
        # Check for methodology clarity
        if op_data.get("methodology_clear", True):
            score += 0.05
        
        return ReproducibilityInfo(
            code_available=has_code,
            code_url=op_data.get("code_url", ""),
            data_available=has_data,
            data_url=op_data.get("data_url", ""),
            hardware_requirements=hardware,
            estimated_compute_time=op_data.get("compute_time", ""),
            reproducibility_score=min(score, 1.0)
        )
    
    def _estimate_resources(
        self,
        claim: Dict,
        op_data: Dict
    ) -> ResourceRequirements:
        """Estimate resource requirements."""
        
        # Default to medium scale
        scale = ComputeScale.MODERATE
        
        claim_text = claim.get("claim_text", "").lower()
        
        # Infer scale from claim text
        if any(kw in claim_text for kw in ["large-scale", "distributed", "cluster"]):
            scale = ComputeScale.HIGH
        elif any(kw in claim_text for kw in ["minimal", "simple", "lightweight"]):
            scale = ComputeScale.LOW
        elif any(kw in claim_text for kw in ["pretrain", "foundation", "billion"]):
            scale = ComputeScale.EXTREME
        
        # Extract from operationalization data
        gpu_hours = op_data.get("estimated_gpu_hours", 0)
        if gpu_hours == 0:
            # Estimate based on scale
            gpu_hours_map = {
                ComputeScale.LOW: 10,
                ComputeScale.MODERATE: 100,
                ComputeScale.HIGH: 1000,
                ComputeScale.EXTREME: 10000
            }
            gpu_hours = gpu_hours_map.get(scale, 100)
        
        # Infer libraries from claim
        libraries = op_data.get("libraries", [])
        if not libraries:
            if "pytorch" in claim_text or "torch" in claim_text:
                libraries.append("PyTorch")
            if "tensorflow" in claim_text:
                libraries.append("TensorFlow")
            if "transformer" in claim_text:
                libraries.append("Transformers")
        
        return ResourceRequirements(
            compute_scale=scale,
            estimated_gpu_hours=gpu_hours,
            estimated_memory_gb=op_data.get("memory_gb", 16),
            required_libraries=libraries,
            external_services=op_data.get("external_services", []),
            estimated_cost_usd=gpu_hours * 0.5  # Rough estimate
        )
    
    def _generate_action_description(self, claim_text: str) -> str:
        """Generate an action description from claim text."""
        # Convert claim to action-oriented language
        
        # Simple transformation: add "Implement" prefix and action verbs
        if claim_text.startswith("The ") or claim_text.startswith("This "):
            description = f"Implement: {claim_text}"
        elif not any(claim_text.startswith(verb) for verb in 
                     ["Implement", "Create", "Build", "Design", "Develop"]):
            description = f"Implement {claim_text}"
        else:
            description = claim_text
        
        return description[:500]  # Limit length
    
    def _estimate_hours(self, claim: Dict, op_data: Dict) -> float:
        """Estimate implementation hours."""
        base_hours = 8.0  # Default to 1 day
        
        # Adjust based on complexity indicators
        claim_text = claim.get("claim_text", "").lower()
        
        if any(kw in claim_text for kw in ["novel", "new architecture", "design"]):
            base_hours *= 2
        
        if any(kw in claim_text for kw in ["simple", "straightforward", "standard"]):
            base_hours *= 0.5
        
        if any(kw in claim_text for kw in ["system", "framework", "pipeline"]):
            base_hours *= 1.5
        
        # Use operationalization estimate if available
        if op_data.get("estimated_implementation_hours"):
            base_hours = op_data["estimated_implementation_hours"]
        
        return round(base_hours, 1)
    
    def _calculate_complexity(self, claim: Dict, op_data: Dict) -> float:
        """Calculate complexity score (0-1)."""
        score = 0.5
        
        claim_text = claim.get("claim_text", "").lower()
        
        # Increase for complexity indicators
        if any(kw in claim_text for kw in ["complex", "sophisticated", "advanced"]):
            score += 0.2
        
        # Decrease for simplicity indicators
        if any(kw in claim_text for kw in ["simple", "basic", "standard"]):
            score -= 0.2
        
        # Increase for integration requirements
        if len(claim.get("requirement_mappings", [])) > 2:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _sort_claims_by_dependency(self, claims: List[Dict]) -> List[Dict]:
        """Sort claims by inferred dependencies."""
        # Simple heuristic: data/setup claims first, evaluation last
        
        def claim_priority(claim):
            text = claim.get("claim_text", "").lower()
            
            if any(kw in text for kw in ["data", "dataset", "preprocess"]):
                return 0
            elif any(kw in text for kw in ["architecture", "model", "design"]):
                return 1
            elif any(kw in text for kw in ["train", "optimize", "learn"]):
                return 2
            elif any(kw in text for kw in ["evaluate", "benchmark", "test"]):
                return 3
            else:
                return 1.5
        
        return sorted(claims, key=claim_priority)
    
    def _resolve_dependencies(self):
        """Resolve cross-chain dependencies."""
        # Build action index
        action_index: Dict[str, GeneratedAction] = {}
        for action in self.actions:
            action_index[action.generation_id] = action
        
        # Update successor IDs
        for chain in self.chains:
            for i, action in enumerate(chain.actions):
                if i < len(chain.actions) - 1:
                    next_id = chain.actions[i + 1].generation_id
                    action.action_vector.chain_position.successor_id = next_id
                    
                    # Also update blocks
                    if next_id not in action.blocks:
                        action.blocks.append(next_id)
        
        # Look for cross-chain dependencies based on resource sharing
        # (This is a simplified version; could be enhanced with semantic analysis)
    
    def _calculate_priorities(self):
        """Calculate action priorities."""
        
        # Build pillar priority map
        pillar_priority = {
            "Pillar 1": ActionPriority.CRITICAL,
            "Pillar 2": ActionPriority.HIGH,
            "Pillar 3": ActionPriority.CRITICAL,
            "Pillar 4": ActionPriority.HIGH,
            "Pillar 5": ActionPriority.CRITICAL,
            "Pillar 6": ActionPriority.MEDIUM,
            "Pillar 7": ActionPriority.MEDIUM,
        }
        
        for action in self.actions:
            # Check pillar priority
            for pillar, priority in pillar_priority.items():
                if pillar in action.action_vector.target_requirement_ids:
                    action.priority = priority
                    break
            
            # Boost priority for first-in-chain (enablers)
            if action.action_vector.chain_position.is_first:
                if action.priority == ActionPriority.MEDIUM:
                    action.priority = ActionPriority.HIGH
            
            # High reproducibility = higher priority (safer to implement)
            if action.action_vector.reproducibility.reproducibility_score > 0.8:
                if action.priority == ActionPriority.MEDIUM:
                    action.priority = ActionPriority.HIGH
    
    def _generate_output(self) -> Dict:
        """Generate the final output dictionary."""
        summary = self._calculate_summary()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "chains": [chain.to_dict() for chain in self.chains],
            "all_actions": [action.to_dict() for action in self.actions],
            "priority_breakdown": self._priority_breakdown(),
            "resource_totals": self._resource_totals()
        }
    
    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics."""
        for chain in self.chains:
            chain.calculate_metrics()
        
        return {
            "total_actions": len(self.actions),
            "total_chains": len(self.chains),
            "total_estimated_hours": sum(a.estimated_hours for a in self.actions),
            "critical_actions": sum(
                1 for a in self.actions 
                if a.priority == ActionPriority.CRITICAL
            ),
            "high_reproducibility_actions": sum(
                1 for a in self.actions 
                if a.action_vector.reproducibility.reproducibility_score > 0.7
            ),
            "avg_complexity": sum(a.complexity_score for a in self.actions) / len(self.actions) if self.actions else 0
        }
    
    def _priority_breakdown(self) -> Dict:
        """Get breakdown by priority."""
        breakdown = defaultdict(list)
        
        for action in self.actions:
            breakdown[action.priority.value].append({
                "action_id": action.generation_id,
                "description": action.action_vector.description[:100]
            })
        
        return dict(breakdown)
    
    def _resource_totals(self) -> Dict:
        """Calculate total resource requirements."""
        total_gpu_hours = sum(
            a.action_vector.resources.estimated_gpu_hours 
            for a in self.actions
        )
        total_cost = sum(
            a.action_vector.resources.estimated_cost_usd 
            for a in self.actions
        )
        
        all_libraries = set()
        for a in self.actions:
            all_libraries.update(a.action_vector.resources.required_libraries)
        
        return {
            "total_gpu_hours": total_gpu_hours,
            "total_estimated_cost_usd": round(total_cost, 2),
            "all_required_libraries": list(all_libraries)
        }
    
    def _generate_id(self, source: str) -> str:
        """Generate a unique ID from source string."""
        return hashlib.md5(source.encode()).hexdigest()[:12]
    
    def save_actions(self, output_path: str) -> Dict:
        """Save actions to file."""
        output = self._generate_output()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.actions)} actions to {output_path}")
        return output


def generate_action_vectors(
    pillar_definitions_path: str,
    approved_claims_path: str,
    output_path: str,
    operationalization_path: Optional[str] = None
) -> Dict:
    """
    Convenience function to generate action vectors.
    
    Args:
        pillar_definitions_path: Path to pillar definitions
        approved_claims_path: Path to approved claims JSON
        output_path: Path to save action vectors
        operationalization_path: Optional path to operationalization data
    
    Returns:
        Generated action vectors dictionary
    """
    with open(approved_claims_path, 'r', encoding='utf-8') as f:
        claims = json.load(f)
    
    operationalization = None
    if operationalization_path and Path(operationalization_path).exists():
        with open(operationalization_path, 'r', encoding='utf-8') as f:
            operationalization = json.load(f)
    
    generator = ActionGenerator(pillar_definitions_path)
    generator.generate_actions(claims, operationalization)
    
    return generator.save_actions(output_path)
```

---

### 2. Orchestrator Integration

**File:** `literature_review/orchestrator.py` (additions)

```python
# Add to imports
from literature_review.analysis.action_generator import (
    ActionGenerator,
    generate_action_vectors
)

# Add method to orchestrator
def generate_action_vectors(
    self,
    output_path: Optional[str] = None
) -> Dict:
    """
    Generate action vectors from approved claims.
    
    Args:
        output_path: Optional custom output path
    
    Returns:
        Action vectors dictionary
    """
    output_path = output_path or os.path.join(
        self.output_dir, "action_vectors.json"
    )
    
    # Get approved claims from version history
    approved_claims = self._get_approved_claims()
    
    # Get operationalization data if available
    operationalization_path = os.path.join(
        self.output_dir, "operationalization_data.json"
    )
    
    result = generate_action_vectors(
        pillar_definitions_path=self.pillar_definitions_path,
        approved_claims_path=None,  # Pass claims directly
        output_path=output_path,
        operationalization_path=operationalization_path if Path(operationalization_path).exists() else None
    )
    
    logger.info(f"Generated {result['summary']['total_actions']} action vectors")
    return result

def _get_approved_claims(self) -> List[Dict]:
    """Extract approved claims from version history."""
    approved = []
    
    for paper_id, paper_data in self.version_history.items():
        claims = paper_data.get("claims", [])
        for claim in claims:
            if claim.get("approved", claim.get("status") == "approved"):
                claim["paper_id"] = paper_id
                approved.append(claim)
    
    return approved
```

---

## Unit Tests

**File:** `tests/unit/test_action_generator.py`

```python
"""Unit tests for action generator."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from literature_review.analysis.action_generator import (
    ActionGenerator,
    GeneratedAction,
    ActionChain,
    ActionPriority,
    ActionStatus
)
from literature_review.models import (
    ActionVector,
    ReproducibilityInfo,
    ResourceRequirements,
    ActionChainPosition,
    ComputeScale
)


class TestGeneratedAction:
    """Tests for GeneratedAction dataclass."""
    
    def test_create_generated_action(self):
        """Test creating a generated action."""
        action_vector = ActionVector(
            action_id="test-001",
            description="Test action",
            source_paper_id="paper-001",
            source_claim="Test claim",
            reproducibility=ReproducibilityInfo(),
            resources=ResourceRequirements(),
            chain_position=ActionChainPosition()
        )
        
        generated = GeneratedAction(
            action_vector=action_vector,
            generation_id="gen-001",
            priority=ActionPriority.HIGH
        )
        
        assert generated.generation_id == "gen-001"
        assert generated.priority == ActionPriority.HIGH
    
    def test_to_dict(self):
        """Test serialization."""
        action_vector = ActionVector(
            action_id="test-001",
            description="Test action",
            source_paper_id="paper-001",
            source_claim="Test claim",
            reproducibility=ReproducibilityInfo(),
            resources=ResourceRequirements(),
            chain_position=ActionChainPosition()
        )
        
        generated = GeneratedAction(action_vector=action_vector)
        data = generated.to_dict()
        
        assert "action_vector" in data
        assert "priority" in data


class TestActionChain:
    """Tests for ActionChain."""
    
    def test_calculate_metrics_empty(self):
        """Test metrics for empty chain."""
        chain = ActionChain(
            chain_id="chain-001",
            name="Test Chain",
            description="Test"
        )
        
        chain.calculate_metrics()
        
        assert chain.total_actions == 0
        assert chain.total_hours == 0
    
    def test_calculate_metrics_with_actions(self):
        """Test metrics with actions."""
        chain = ActionChain(
            chain_id="chain-001",
            name="Test Chain",
            description="Test"
        )
        
        for i in range(3):
            action_vector = ActionVector(
                action_id=f"test-{i}",
                description=f"Action {i}",
                source_paper_id="paper",
                source_claim="claim",
                reproducibility=ReproducibilityInfo(),
                resources=ResourceRequirements(),
                chain_position=ActionChainPosition()
            )
            
            generated = GeneratedAction(
                action_vector=action_vector,
                generation_id=f"gen-{i}",
                estimated_hours=4.0,
                status=ActionStatus.COMPLETED if i == 0 else ActionStatus.PENDING
            )
            
            chain.actions.append(generated)
        
        chain.calculate_metrics()
        
        assert chain.total_actions == 3
        assert chain.completed_actions == 1
        assert chain.total_hours == 12.0


class TestActionGenerator:
    """Tests for ActionGenerator class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1: Sensory Transduction": [
                        {"id": "Sub-1.1.1", "text": "Sensory model"}
                    ]
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_claims(self):
        """Create sample approved claims."""
        return [
            {
                "claim_id": "claim-001",
                "claim_text": "This architecture achieves 95% accuracy on benchmark",
                "pillar": "Pillar 1",
                "requirement": "REQ-B1.1",
                "requirement_mappings": ["Sub-1.1.1"],
                "approved": True
            },
            {
                "claim_id": "claim-002",
                "claim_text": "The data preprocessing pipeline handles raw signals",
                "pillar": "Pillar 1",
                "requirement": "REQ-B1.1",
                "requirement_mappings": ["Sub-1.1.1"],
                "approved": True
            }
        ]
    
    def test_generate_actions(self, sample_pillar_definitions, sample_claims):
        """Test action generation."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(sample_claims)
        
        assert "summary" in result
        assert result["summary"]["total_actions"] == 2
    
    def test_chain_creation(self, sample_pillar_definitions, sample_claims):
        """Test chain creation."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(sample_claims)
        
        assert len(result["chains"]) == 1
        assert result["chains"][0]["total_actions"] == 2
    
    def test_dependency_ordering(self, sample_pillar_definitions, sample_claims):
        """Test that data claims come before evaluation claims."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(sample_claims)
        
        actions = result["all_actions"]
        
        # Data claim should come first
        assert "data" in actions[0]["action_vector"]["description"].lower() or \
               "preprocess" in actions[0]["action_vector"]["description"].lower()
    
    def test_reproducibility_assessment(self, sample_pillar_definitions):
        """Test reproducibility assessment."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Code available at github.com/example, trained on ImageNet dataset",
            "pillar": "Pillar 1",
            "requirement": "REQ-B1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        repro = action["action_vector"]["reproducibility"]
        
        # Should detect code availability from claim text
        assert repro["code_available"] is True
    
    def test_resource_estimation(self, sample_pillar_definitions):
        """Test resource estimation."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Large-scale distributed training on cluster with PyTorch",
            "pillar": "Pillar 1",
            "requirement": "REQ-B1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        resources = action["action_vector"]["resources"]
        
        # Should detect high compute scale
        assert resources["compute_scale"] == "high"
        assert "PyTorch" in resources["required_libraries"]
    
    def test_save_actions(self, sample_pillar_definitions, sample_claims, tmp_path):
        """Test saving actions to file."""
        generator = ActionGenerator(sample_pillar_definitions)
        generator.generate_actions(sample_claims)
        
        output_path = str(tmp_path / "action_vectors.json")
        result = generator.save_actions(output_path)
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_actions"] == 2
    
    def test_priority_calculation(self, sample_pillar_definitions):
        """Test priority calculation."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Critical for Pillar 1 foundation",
            "pillar": "Pillar 1",
            "requirement": "REQ-B1.1",
            "requirement_mappings": ["Pillar 1"]
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        # Pillar 1 actions should be critical or high priority
        action = result["all_actions"][0]
        assert action["priority"] in ["critical", "high"]


class TestResourceTotals:
    """Tests for resource total calculations."""
    
    def test_resource_aggregation(self, tmp_path):
        """Test that resource totals are aggregated correctly."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {"REQ-1.1": [{"id": "Sub-1.1.1", "text": "Test"}]}
            }
        }
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        claims = [
            {"claim_id": "1", "claim_text": "PyTorch training", "pillar": "Pillar 1", "requirement": "REQ-1.1"},
            {"claim_id": "2", "claim_text": "TensorFlow inference", "pillar": "Pillar 1", "requirement": "REQ-1.1"}
        ]
        
        generator = ActionGenerator(str(path))
        result = generator.generate_actions(claims)
        
        totals = result["resource_totals"]
        
        assert totals["total_gpu_hours"] > 0
        assert "PyTorch" in totals["all_required_libraries"]
        assert "TensorFlow" in totals["all_required_libraries"]
```

---

## Output Schema: `action_vectors.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "summary": {
    "total_actions": 45,
    "total_chains": 12,
    "total_estimated_hours": 580,
    "critical_actions": 15,
    "high_reproducibility_actions": 28,
    "avg_complexity": 0.55
  },
  "chains": [
    {
      "chain_id": "abc123def456",
      "name": "Actions for REQ-B1.1: Sensory Transduction",
      "description": "Implementation actions derived from 5 approved claims",
      "target_pillar": "Pillar 1: Biological Stimulus-Response",
      "target_requirement": "REQ-B1.1",
      "total_actions": 5,
      "completed_actions": 0,
      "blocked_actions": 0,
      "total_hours": 52,
      "critical_path_hours": 40,
      "completion_percentage": 0,
      "actions": [
        {
          "action_vector": {
            "action_id": "xyz789abc012",
            "description": "Implement: Data preprocessing pipeline for raw neural signals",
            "source_paper_id": "paper-2024-neural-encoding.pdf",
            "source_claim": "The data preprocessing pipeline handles raw signals",
            "reproducibility": {
              "code_available": true,
              "code_url": "https://github.com/example/neural-preprocess",
              "data_available": true,
              "data_url": "",
              "hardware_requirements": ["GPU"],
              "estimated_compute_time": "2 hours",
              "reproducibility_score": 0.85
            },
            "resources": {
              "compute_scale": "moderate",
              "estimated_gpu_hours": 50,
              "estimated_memory_gb": 32,
              "required_libraries": ["PyTorch", "NumPy"],
              "external_services": [],
              "estimated_cost_usd": 25.0
            },
            "chain_position": {
              "chain_id": "abc123def456",
              "position_in_chain": 0,
              "total_chain_length": 5,
              "is_first": true,
              "is_last": false,
              "predecessor_id": null,
              "successor_id": "xyz789abc013"
            },
            "validation_requirements": ["fMRI correlation > 0.7"],
            "target_requirement_ids": ["Sub-1.1.1", "Sub-1.1.2"]
          },
          "generation_id": "xyz789abc012",
          "generated_at": "2025-12-19T10:00:00Z",
          "source_claims": ["claim-001"],
          "source_papers": ["paper-2024-neural-encoding.pdf"],
          "pillar_mappings": ["Sub-1.1.1", "Sub-1.1.2"],
          "priority": "high",
          "status": "pending",
          "depends_on": [],
          "blocks": ["xyz789abc013"],
          "estimated_hours": 8.0,
          "complexity_score": 0.5
        }
      ]
    }
  ],
  "priority_breakdown": {
    "critical": [{"action_id": "...", "description": "..."}],
    "high": [{"action_id": "...", "description": "..."}],
    "medium": [],
    "low": []
  },
  "resource_totals": {
    "total_gpu_hours": 2400,
    "total_estimated_cost_usd": 1200.00,
    "all_required_libraries": ["PyTorch", "TensorFlow", "Transformers", "NumPy", "SciPy"]
  }
}
```

---

## Acceptance Criteria Checklist

- [ ] ActionGenerator correctly groups claims by pillar/requirement
- [ ] Claims sorted by dependency (data → model → training → evaluation)
- [ ] Chain dependencies correctly computed (predecessor/successor)
- [ ] Reproducibility assessed from claim text and operationalization data
- [ ] Resource requirements estimated from keywords and operationalization
- [ ] Priorities assigned based on pillar importance and chain position
- [ ] Resource totals correctly aggregated
- [ ] Actions saved in correct JSON format
- [ ] Unit tests pass with >90% coverage

---

## Notes for Agent

1. **Run standalone for testing:**
   ```python
   from literature_review.analysis.action_generator import ActionGenerator
   
   generator = ActionGenerator("pillar_definitions_enhanced.json")
   
   claims = [
       {"claim_text": "Model achieves 95% accuracy", "pillar": "Pillar 1", "requirement": "REQ-1.1"}
   ]
   
   result = generator.generate_actions(claims)
   print(json.dumps(result["summary"], indent=2))
   ```

2. **Integration with operationalization:**
   - Best used after OP-W2-1 (Action Extraction) runs
   - Operationalization data enhances resource/reproducibility estimates
   - Falls back to heuristics if operationalization not available

3. **Critical path calculation:**
   - Uses simple longest-path algorithm
   - Assumes sequential dependency within chains
   - Cross-chain dependencies tracked but not used in critical path
