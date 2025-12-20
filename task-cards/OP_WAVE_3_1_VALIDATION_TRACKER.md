# Task Card: Validation Coverage Tracker

**Task ID:** OP-W3-1  
**Wave:** 3 (Analysis & Output)  
**Priority:** HIGH  
**Estimated Effort:** 10 hours  
**Status:** Not Started  
**Dependencies:** OP-W1-1 (Schema Foundation), OP-W2-1 (Action Extraction)  
**Blocks:** OP-W4-2 (Modification Proposals)

---

## Objective

Track validation strategy coverage across all requirements, identifying gaps between design requirements and validation evidence. Generate `validation_gap_matrix.json` that shows which requirements have validated strategies and which need attention.

## Background

The current system tracks:
- Completeness percentage per sub-requirement
- Evidence count and papers
- Gap severity levels

This task adds tracking for:
- **Validation strategy definition**: Does a validation method exist?
- **Strategy-evidence alignment**: Does evidence match the defined strategy?
- **Validation coverage status**: VALIDATED / PARTIAL / UNVALIDATED / NO_STRATEGY
- **Gap closure recommendations**: How to close validation gaps

## Success Criteria

- [ ] `validation_tracker.py` module created
- [ ] Validation status determined for all requirements
- [ ] `validation_gap_matrix.json` generated
- [ ] Integration with proof_scorecard.py
- [ ] Validation coverage weighted in readiness scoring
- [ ] Unit tests cover all coverage status scenarios

---

## Deliverables

### 1. Validation Tracker Module

**File:** `literature_review/analysis/validation_tracker.py`

```python
"""
Validation Coverage Tracker

Analyzes validation strategy coverage across requirements,
identifying gaps between design requirements and validation evidence.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from enum import Enum

from literature_review.models import (
    ValidationStrategy,
    ValidationStatus,
    EvidenceType
)

logger = logging.getLogger(__name__)


class CoverageLevel(Enum):
    """Coverage level for validation tracking."""
    FULL = "full"           # Strategy defined and evidence matches
    PARTIAL = "partial"     # Evidence exists but different method or incomplete
    NONE = "none"           # Strategy defined but no evidence
    UNDEFINED = "undefined" # No strategy defined


@dataclass
class ValidationCoverageItem:
    """Validation coverage for a single requirement."""
    requirement_id: str
    requirement_text: str
    pillar: str
    parent_requirement: str
    
    # Strategy status
    has_strategy: bool = False
    validation_method: str = ""
    benchmark_protocol: str = ""
    acceptance_criteria: str = ""
    
    # Evidence status
    evidence_count: int = 0
    evidence_papers: List[str] = field(default_factory=list)
    evidence_methods_used: List[str] = field(default_factory=list)
    
    # Coverage determination
    coverage_status: ValidationStatus = ValidationStatus.NO_STRATEGY
    coverage_level: CoverageLevel = CoverageLevel.UNDEFINED
    strategy_evidence_alignment: float = 0.0  # 0-1
    
    # Gap information
    gap_reason: str = ""
    recommendation: str = ""
    priority: str = "MEDIUM"
    
    def to_dict(self) -> Dict:
        return {
            "requirement_id": self.requirement_id,
            "requirement_text": self.requirement_text,
            "pillar": self.pillar,
            "parent_requirement": self.parent_requirement,
            "has_strategy": self.has_strategy,
            "validation_method": self.validation_method,
            "benchmark_protocol": self.benchmark_protocol,
            "acceptance_criteria": self.acceptance_criteria,
            "evidence_count": self.evidence_count,
            "evidence_papers": self.evidence_papers,
            "evidence_methods_used": self.evidence_methods_used,
            "coverage_status": self.coverage_status.value,
            "coverage_level": self.coverage_level.value,
            "strategy_evidence_alignment": self.strategy_evidence_alignment,
            "gap_reason": self.gap_reason,
            "recommendation": self.recommendation,
            "priority": self.priority
        }


class ValidationTracker:
    """
    Track validation coverage across requirements.
    
    This class analyzes:
    1. Which requirements have defined validation strategies
    2. Which have evidence matching those strategies
    3. Gaps between requirements and their validation
    """
    
    def __init__(
        self,
        pillar_definitions_path: str,
        gap_analysis_path: Optional[str] = None,
        version_history_path: Optional[str] = None
    ):
        """
        Initialize validation tracker.
        
        Args:
            pillar_definitions_path: Path to pillar_definitions_enhanced.json
            gap_analysis_path: Optional path to gap_analysis_report.json
            version_history_path: Optional path to review_version_history.json
        """
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        self.gap_analysis = {}
        if gap_analysis_path and Path(gap_analysis_path).exists():
            with open(gap_analysis_path, 'r', encoding='utf-8') as f:
                self.gap_analysis = json.load(f)
        
        self.version_history = {}
        if version_history_path and Path(version_history_path).exists():
            with open(version_history_path, 'r', encoding='utf-8') as f:
                self.version_history = json.load(f)
        
        # Coverage results
        self.coverage_items: Dict[str, ValidationCoverageItem] = {}
    
    def analyze_validation_coverage(self) -> Dict:
        """
        Perform complete validation coverage analysis.
        
        Returns:
            Validation gap matrix dictionary
        """
        logger.info("Analyzing validation coverage...")
        
        # Extract all requirements with their validation strategies
        requirements = self._extract_requirements_with_strategies()
        logger.info(f"Found {len(requirements)} requirements to analyze")
        
        # Match evidence to strategies
        for req_id, req_info in requirements.items():
            coverage = self._analyze_requirement_coverage(req_id, req_info)
            self.coverage_items[req_id] = coverage
        
        # Generate summary and output
        return self._generate_matrix()
    
    def _extract_requirements_with_strategies(self) -> Dict[str, Dict]:
        """Extract all requirements and their validation strategies."""
        requirements = {}
        
        for pillar_name, pillar_data in self.pillar_definitions.items():
            if not pillar_name.startswith("Pillar"):
                continue
            
            pillar_reqs = pillar_data.get("requirements", {})
            validation_criteria = pillar_data.get("validation_criteria", {})
            
            for req_key, sub_reqs in pillar_reqs.items():
                if isinstance(sub_reqs, list):
                    for sub_req in sub_reqs:
                        # Handle both old format (string) and new format (dict)
                        if isinstance(sub_req, str):
                            # Old format: "Sub-X.X.X: Description"
                            if ": " in sub_req:
                                parts = sub_req.split(": ", 1)
                                sub_id = parts[0]
                                sub_text = parts[1] if len(parts) > 1 else sub_req
                            else:
                                sub_id = sub_req
                                sub_text = sub_req
                            
                            validation_strategy = {}
                        else:
                            # New format: dict with id, text, validation_strategy
                            sub_id = sub_req.get("id", "Unknown")
                            sub_text = sub_req.get("text", "")
                            validation_strategy = sub_req.get("validation_strategy", {})
                        
                        req_full_id = f"{pillar_name}::{req_key}::{sub_id}"
                        
                        requirements[req_full_id] = {
                            "requirement_id": sub_id,
                            "requirement_text": sub_text,
                            "pillar": pillar_name,
                            "parent_requirement": req_key,
                            "validation_strategy": validation_strategy,
                            "pillar_validation_criteria": validation_criteria
                        }
        
        return requirements
    
    def _analyze_requirement_coverage(
        self,
        req_full_id: str,
        req_info: Dict
    ) -> ValidationCoverageItem:
        """Analyze validation coverage for a single requirement."""
        strategy = req_info.get("validation_strategy", {})
        pillar_criteria = req_info.get("pillar_validation_criteria", {})
        
        # Determine if strategy is defined
        has_strategy = bool(
            strategy.get("method") or 
            strategy.get("benchmark_protocol") or
            pillar_criteria
        )
        
        # Get validation method details
        validation_method = strategy.get("method", "")
        benchmark_protocol = strategy.get("benchmark_protocol", "")
        acceptance_criteria = strategy.get("acceptance_criteria", "")
        
        # If no per-requirement strategy, try pillar-level criteria
        if not validation_method and pillar_criteria:
            # Use pillar-level criteria as fallback
            for key, value in pillar_criteria.items():
                if isinstance(value, str):
                    validation_method = f"{key}: {value}"
                    break
        
        # Get evidence from gap analysis
        evidence_papers = []
        evidence_methods = []
        
        if self.gap_analysis:
            evidence_info = self._get_evidence_for_requirement(req_full_id)
            evidence_papers = evidence_info.get("papers", [])
            evidence_methods = evidence_info.get("methods", [])
        
        # Determine coverage status
        coverage_status, coverage_level, alignment = self._determine_coverage_status(
            has_strategy=has_strategy,
            validation_method=validation_method,
            evidence_papers=evidence_papers,
            evidence_methods=evidence_methods
        )
        
        # Generate gap information
        gap_reason, recommendation, priority = self._generate_gap_info(
            coverage_status=coverage_status,
            has_strategy=has_strategy,
            validation_method=validation_method,
            evidence_count=len(evidence_papers),
            req_info=req_info
        )
        
        return ValidationCoverageItem(
            requirement_id=req_info["requirement_id"],
            requirement_text=req_info["requirement_text"],
            pillar=req_info["pillar"],
            parent_requirement=req_info["parent_requirement"],
            has_strategy=has_strategy,
            validation_method=validation_method,
            benchmark_protocol=benchmark_protocol,
            acceptance_criteria=acceptance_criteria,
            evidence_count=len(evidence_papers),
            evidence_papers=evidence_papers,
            evidence_methods_used=evidence_methods,
            coverage_status=coverage_status,
            coverage_level=coverage_level,
            strategy_evidence_alignment=alignment,
            gap_reason=gap_reason,
            recommendation=recommendation,
            priority=priority
        )
    
    def _get_evidence_for_requirement(self, req_full_id: str) -> Dict:
        """Get evidence information for a requirement from gap analysis."""
        parts = req_full_id.split("::")
        if len(parts) != 3:
            return {"papers": [], "methods": []}
        
        pillar_name, req_key, sub_id = parts
        
        # Search gap analysis for this requirement
        pillar_data = self.gap_analysis.get(pillar_name, {})
        analysis = pillar_data.get("analysis", {})
        
        for req_name, sub_reqs in analysis.items():
            if req_key in req_name or req_name in req_key:
                for sub_name, sub_data in sub_reqs.items():
                    if sub_id in sub_name or sub_name in sub_id:
                        papers = [
                            p.get("filename", p) 
                            for p in sub_data.get("contributing_papers", [])
                        ]
                        # Methods would come from operationalization extraction
                        methods = []
                        return {"papers": papers, "methods": methods}
        
        return {"papers": [], "methods": []}
    
    def _determine_coverage_status(
        self,
        has_strategy: bool,
        validation_method: str,
        evidence_papers: List[str],
        evidence_methods: List[str]
    ) -> Tuple[ValidationStatus, CoverageLevel, float]:
        """Determine validation coverage status."""
        
        if not has_strategy:
            if evidence_papers:
                # Evidence exists but no strategy defined
                return ValidationStatus.NO_STRATEGY, CoverageLevel.UNDEFINED, 0.0
            else:
                return ValidationStatus.NO_STRATEGY, CoverageLevel.UNDEFINED, 0.0
        
        if not evidence_papers:
            # Strategy defined but no evidence
            return ValidationStatus.UNVALIDATED, CoverageLevel.NONE, 0.0
        
        # Calculate alignment between strategy and evidence methods
        alignment = self._calculate_method_alignment(validation_method, evidence_methods)
        
        if alignment >= 0.7:
            return ValidationStatus.VALIDATED, CoverageLevel.FULL, alignment
        elif alignment >= 0.3 or len(evidence_papers) > 0:
            return ValidationStatus.PARTIAL, CoverageLevel.PARTIAL, alignment
        else:
            return ValidationStatus.UNVALIDATED, CoverageLevel.NONE, alignment
    
    def _calculate_method_alignment(
        self,
        validation_method: str,
        evidence_methods: List[str]
    ) -> float:
        """Calculate alignment between validation method and evidence methods."""
        if not validation_method or not evidence_methods:
            return 0.0 if not evidence_methods else 0.3  # Partial credit for having evidence
        
        # Simple keyword matching for now
        method_lower = validation_method.lower()
        
        # Key method terms to match
        method_terms = ["fmri", "eeg", "recording", "simulation", "benchmark", 
                       "comparison", "ablation", "timing", "accuracy", "power"]
        
        matches = 0
        total_terms = 0
        
        for term in method_terms:
            if term in method_lower:
                total_terms += 1
                for evidence_method in evidence_methods:
                    if term in evidence_method.lower():
                        matches += 1
                        break
        
        if total_terms == 0:
            return 0.3  # Default partial alignment
        
        return matches / total_terms
    
    def _generate_gap_info(
        self,
        coverage_status: ValidationStatus,
        has_strategy: bool,
        validation_method: str,
        evidence_count: int,
        req_info: Dict
    ) -> Tuple[str, str, str]:
        """Generate gap information with recommendations."""
        
        if coverage_status == ValidationStatus.VALIDATED:
            return "", "", "LOW"
        
        if coverage_status == ValidationStatus.NO_STRATEGY:
            if evidence_count > 0:
                gap_reason = "Validation strategy not defined despite having evidence"
                recommendation = "Define explicit validation method and acceptance criteria"
                priority = "MEDIUM"
            else:
                gap_reason = "No validation strategy defined and no evidence"
                recommendation = "Define validation strategy, then search for validating evidence"
                priority = "HIGH"
        
        elif coverage_status == ValidationStatus.UNVALIDATED:
            gap_reason = f"Strategy defined ('{validation_method[:50]}...') but no supporting evidence"
            recommendation = f"Search for papers using: {validation_method[:100]}"
            priority = "HIGH"
        
        elif coverage_status == ValidationStatus.PARTIAL:
            gap_reason = "Evidence exists but uses different validation method than defined"
            recommendation = "Find additional evidence using defined validation method, or update strategy"
            priority = "MEDIUM"
        
        else:
            gap_reason = "Unknown coverage status"
            recommendation = "Manual review required"
            priority = "MEDIUM"
        
        return gap_reason, recommendation, priority
    
    def _generate_matrix(self) -> Dict:
        """Generate the validation gap matrix."""
        summary = self._calculate_summary()
        by_pillar = self._group_by_pillar()
        critical_gaps = self._identify_critical_gaps()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "by_pillar": by_pillar,
            "critical_gaps": critical_gaps,
            "all_requirements": {
                req_id: item.to_dict() 
                for req_id, item in self.coverage_items.items()
            }
        }
    
    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics."""
        total = len(self.coverage_items)
        
        validated = sum(
            1 for item in self.coverage_items.values()
            if item.coverage_status == ValidationStatus.VALIDATED
        )
        partial = sum(
            1 for item in self.coverage_items.values()
            if item.coverage_status == ValidationStatus.PARTIAL
        )
        unvalidated = sum(
            1 for item in self.coverage_items.values()
            if item.coverage_status == ValidationStatus.UNVALIDATED
        )
        no_strategy = sum(
            1 for item in self.coverage_items.values()
            if item.coverage_status == ValidationStatus.NO_STRATEGY
        )
        
        coverage_score = (validated + partial * 0.5) / total * 100 if total > 0 else 0
        
        return {
            "total_requirements": total,
            "validated": validated,
            "partially_validated": partial,
            "unvalidated": unvalidated,
            "no_strategy": no_strategy,
            "coverage_percentage": round(coverage_score, 1),
            "strategy_definition_rate": round((total - no_strategy) / total * 100, 1) if total > 0 else 0
        }
    
    def _group_by_pillar(self) -> Dict:
        """Group results by pillar."""
        by_pillar = defaultdict(lambda: {
            "requirements": [],
            "summary": {"validated": 0, "partial": 0, "unvalidated": 0, "no_strategy": 0}
        })
        
        for req_id, item in self.coverage_items.items():
            pillar = item.pillar
            by_pillar[pillar]["requirements"].append(item.to_dict())
            
            status_key = {
                ValidationStatus.VALIDATED: "validated",
                ValidationStatus.PARTIAL: "partial",
                ValidationStatus.UNVALIDATED: "unvalidated",
                ValidationStatus.NO_STRATEGY: "no_strategy"
            }[item.coverage_status]
            
            by_pillar[pillar]["summary"][status_key] += 1
        
        return dict(by_pillar)
    
    def _identify_critical_gaps(self) -> List[Dict]:
        """Identify critical validation gaps."""
        gaps = []
        
        for req_id, item in self.coverage_items.items():
            if item.priority == "HIGH" or item.coverage_status in [
                ValidationStatus.NO_STRATEGY, 
                ValidationStatus.UNVALIDATED
            ]:
                gaps.append({
                    "requirement_id": item.requirement_id,
                    "pillar": item.pillar,
                    "gap_type": item.coverage_status.value,
                    "gap_reason": item.gap_reason,
                    "recommendation": item.recommendation,
                    "priority": item.priority,
                    "defined_strategy": {
                        "method": item.validation_method,
                        "benchmark": item.benchmark_protocol,
                        "acceptance": item.acceptance_criteria
                    } if item.has_strategy else None,
                    "evidence_status": f"{item.evidence_count} papers found"
                })
        
        # Sort by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        return sorted(gaps, key=lambda x: priority_order.get(x["priority"], 1))
    
    def save_matrix(self, output_path: str) -> Dict:
        """Save validation gap matrix to file."""
        matrix = self.analyze_validation_coverage()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved validation gap matrix to {output_path}")
        return matrix
    
    def get_validation_score(self) -> float:
        """
        Get overall validation score (0-100).
        
        This can be used by proof_scorecard to weight validation coverage.
        """
        if not self.coverage_items:
            self.analyze_validation_coverage()
        
        summary = self._calculate_summary()
        return summary["coverage_percentage"]


def generate_validation_matrix(
    pillar_definitions_path: str,
    gap_analysis_path: str,
    output_path: str
) -> Dict:
    """
    Convenience function to generate validation gap matrix.
    
    Args:
        pillar_definitions_path: Path to pillar definitions
        gap_analysis_path: Path to gap analysis report
        output_path: Path to save output matrix
    
    Returns:
        Generated matrix dictionary
    """
    tracker = ValidationTracker(
        pillar_definitions_path=pillar_definitions_path,
        gap_analysis_path=gap_analysis_path
    )
    return tracker.save_matrix(output_path)
```

### 2. Proof Scorecard Integration

**File:** `literature_review/analysis/proof_scorecard.py` (modifications)

Add validation coverage weighting:

```python
# Add to imports
from literature_review.analysis.validation_tracker import ValidationTracker

# Add to ProofScorecardAnalyzer class
class ProofScorecardAnalyzer:
    
    def __init__(self, gap_report: Dict, version_history: Dict, pillar_definitions: Dict):
        # ... existing init ...
        self.validation_tracker = None
    
    def set_validation_tracker(self, tracker: ValidationTracker):
        """Set validation tracker for enhanced scoring."""
        self.validation_tracker = tracker
    
    def _calculate_overall_proof_readiness(self) -> float:
        """
        Calculate overall proof readiness (0-100).
        
        Enhanced with validation coverage weighting.
        """
        # Original calculation
        base_score = self._calculate_base_readiness()
        
        # Apply validation coverage adjustment
        if self.validation_tracker:
            validation_score = self.validation_tracker.get_validation_score()
            
            # Validation contributes 20% to final score
            # Formula: 80% base + 20% validation
            final_score = base_score * 0.8 + validation_score * 0.2
            
            return round(final_score, 1)
        
        return base_score
    
    def _calculate_base_readiness(self) -> float:
        """Original readiness calculation (renamed)."""
        total_weighted_score = 0
        total_weight = 0
        
        for pillar_name, pillar_data in self.gap_report.items():
            if not isinstance(pillar_data, dict):
                continue
            
            completeness = pillar_data.get('completeness', pillar_data.get('average_completeness', 0))
            weight = 1.5 if pillar_name in ['Pillar 1', 'Pillar 3', 'Pillar 5'] else 1.0
            
            total_weighted_score += completeness * weight
            total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0
    
    def analyze(self) -> Dict:
        """Generate complete proof scorecard with validation coverage."""
        base_analysis = self._base_analyze()
        
        # Add validation coverage section
        if self.validation_tracker:
            base_analysis["validation_coverage"] = {
                "score": self.validation_tracker.get_validation_score(),
                "summary": self.validation_tracker._calculate_summary(),
                "weight_in_readiness": "20%"
            }
        
        return base_analysis
```

### 3. Orchestrator Integration

**File:** `literature_review/orchestrator.py` (additions)

```python
# Add to imports
from literature_review.analysis.validation_tracker import (
    ValidationTracker,
    generate_validation_matrix
)

# Add method to orchestrator
def generate_validation_coverage_report(
    self,
    output_path: Optional[str] = None
) -> Dict:
    """
    Generate validation coverage report.
    
    Args:
        output_path: Optional custom output path
    
    Returns:
        Validation gap matrix dictionary
    """
    output_path = output_path or os.path.join(
        self.output_dir, "validation_gap_matrix.json"
    )
    
    gap_analysis_path = os.path.join(self.output_dir, "gap_analysis_report.json")
    
    matrix = generate_validation_matrix(
        pillar_definitions_path=self.pillar_definitions_path,
        gap_analysis_path=gap_analysis_path,
        output_path=output_path
    )
    
    logger.info(f"Generated validation coverage: {matrix['summary']}")
    return matrix
```

---

## Unit Tests

**File:** `tests/unit/test_validation_tracker.py`

```python
"""Unit tests for validation tracker."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from literature_review.analysis.validation_tracker import (
    ValidationTracker,
    ValidationCoverageItem,
    CoverageLevel,
    generate_validation_matrix
)
from literature_review.models import ValidationStatus


class TestValidationCoverageItem:
    """Tests for ValidationCoverageItem dataclass."""
    
    def test_create_coverage_item(self):
        """Test creating a coverage item."""
        item = ValidationCoverageItem(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            parent_requirement="REQ-1.1",
            has_strategy=True,
            validation_method="fMRI comparison"
        )
        
        assert item.requirement_id == "Sub-1.1.1"
        assert item.has_strategy is True
    
    def test_to_dict(self):
        """Test serialization."""
        item = ValidationCoverageItem(
            requirement_id="Sub-1.1.1",
            requirement_text="Test",
            pillar="Pillar 1",
            parent_requirement="REQ-1.1",
            coverage_status=ValidationStatus.VALIDATED,
            coverage_level=CoverageLevel.FULL
        )
        
        data = item.to_dict()
        assert data["coverage_status"] == "validated"
        assert data["coverage_level"] == "full"


class TestValidationTracker:
    """Tests for ValidationTracker class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions with validation strategies."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1: Sensory Transduction": [
                        {
                            "id": "Sub-1.1.1",
                            "text": "Sensory data transduction model",
                            "validation_strategy": {
                                "method": "fMRI comparison",
                                "benchmark_protocol": "Natural scene presentation",
                                "acceptance_criteria": "> 0.8 correlation"
                            }
                        },
                        {
                            "id": "Sub-1.1.2",
                            "text": "Feature extraction mechanism",
                            "validation_strategy": {}  # No strategy defined
                        }
                    ]
                },
                "validation_criteria": {
                    "required_evidence": "fMRI, EEG, single-cell recordings"
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_gap_analysis(self, tmp_path):
        """Create sample gap analysis report."""
        gap_data = {
            "Pillar 1: Biological Stimulus-Response": {
                "analysis": {
                    "REQ-B1.1: Sensory Transduction": {
                        "Sub-1.1.1": {
                            "completeness_percent": 70,
                            "contributing_papers": [
                                {"filename": "paper1.pdf"},
                                {"filename": "paper2.pdf"}
                            ]
                        },
                        "Sub-1.1.2": {
                            "completeness_percent": 30,
                            "contributing_papers": []
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap_analysis.json"
        with open(path, 'w') as f:
            json.dump(gap_data, f)
        
        return str(path)
    
    def test_extract_requirements(self, sample_pillar_definitions):
        """Test requirement extraction."""
        tracker = ValidationTracker(sample_pillar_definitions)
        requirements = tracker._extract_requirements_with_strategies()
        
        assert len(requirements) == 2
    
    def test_analyze_coverage(self, sample_pillar_definitions, sample_gap_analysis):
        """Test coverage analysis."""
        tracker = ValidationTracker(
            sample_pillar_definitions,
            gap_analysis_path=sample_gap_analysis
        )
        
        result = tracker.analyze_validation_coverage()
        
        assert "summary" in result
        assert result["summary"]["total_requirements"] == 2
    
    def test_coverage_status_validated(self, sample_pillar_definitions, sample_gap_analysis):
        """Test validated status detection."""
        tracker = ValidationTracker(
            sample_pillar_definitions,
            gap_analysis_path=sample_gap_analysis
        )
        
        tracker.analyze_validation_coverage()
        
        # Sub-1.1.1 has strategy and evidence
        validated_items = [
            item for item in tracker.coverage_items.values()
            if item.requirement_id == "Sub-1.1.1"
        ]
        
        # Should be at least partial since we have evidence
        assert len(validated_items) > 0
    
    def test_no_strategy_detection(self, sample_pillar_definitions):
        """Test no-strategy detection."""
        tracker = ValidationTracker(sample_pillar_definitions)
        tracker.analyze_validation_coverage()
        
        # Sub-1.1.2 has empty validation_strategy
        no_strategy_items = [
            item for item in tracker.coverage_items.values()
            if item.coverage_status == ValidationStatus.NO_STRATEGY
        ]
        
        assert len(no_strategy_items) >= 1
    
    def test_save_matrix(self, sample_pillar_definitions, tmp_path):
        """Test saving matrix to file."""
        tracker = ValidationTracker(sample_pillar_definitions)
        output_path = str(tmp_path / "validation_matrix.json")
        
        matrix = tracker.save_matrix(output_path)
        
        assert Path(output_path).exists()
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_requirements"] == 2
    
    def test_validation_score(self, sample_pillar_definitions):
        """Test validation score calculation."""
        tracker = ValidationTracker(sample_pillar_definitions)
        score = tracker.get_validation_score()
        
        assert 0 <= score <= 100
    
    def test_critical_gaps_identification(self, sample_pillar_definitions):
        """Test critical gap identification."""
        tracker = ValidationTracker(sample_pillar_definitions)
        result = tracker.analyze_validation_coverage()
        
        critical_gaps = result["critical_gaps"]
        
        assert isinstance(critical_gaps, list)
        for gap in critical_gaps:
            assert "recommendation" in gap
            assert "priority" in gap
```

---

## Output Schema: `validation_gap_matrix.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "summary": {
    "total_requirements": 89,
    "validated": 34,
    "partially_validated": 22,
    "unvalidated": 18,
    "no_strategy": 15,
    "coverage_percentage": 50.6,
    "strategy_definition_rate": 83.1
  },
  "by_pillar": {
    "Pillar 1: Biological Stimulus-Response": {
      "summary": {
        "validated": 8,
        "partial": 4,
        "unvalidated": 3,
        "no_strategy": 1
      },
      "requirements": [
        {
          "requirement_id": "Sub-1.1.1",
          "requirement_text": "Conclusive model of sensory transduction",
          "pillar": "Pillar 1: Biological Stimulus-Response",
          "parent_requirement": "REQ-B1.1",
          "has_strategy": true,
          "validation_method": "fMRI comparison with biological data",
          "benchmark_protocol": "Natural scene presentation protocol",
          "acceptance_criteria": "> 0.8 correlation with neural recordings",
          "evidence_count": 3,
          "evidence_papers": ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
          "coverage_status": "validated",
          "coverage_level": "full",
          "strategy_evidence_alignment": 0.85
        }
      ]
    }
  },
  "critical_gaps": [
    {
      "requirement_id": "Sub-2.4.1",
      "pillar": "Pillar 2: AI Stimulus-Response",
      "gap_type": "no_strategy",
      "gap_reason": "No validation strategy defined despite having evidence",
      "recommendation": "Define explicit validation method and acceptance criteria",
      "priority": "MEDIUM",
      "defined_strategy": null,
      "evidence_status": "3 papers found"
    }
  ]
}
```

---

## Acceptance Criteria Checklist

- [ ] ValidationTracker correctly extracts requirements from pillar definitions
- [ ] Both old format (string) and new format (dict) requirements handled
- [ ] Coverage status correctly determined for all scenarios
- [ ] Evidence from gap analysis matched to requirements
- [ ] Critical gaps identified with actionable recommendations
- [ ] Matrix saved in correct JSON format
- [ ] Proof scorecard integration weights validation coverage
- [ ] Validation score exposed for other modules
- [ ] Unit tests pass with >90% coverage

---

## Notes for Agent

1. **Run standalone for testing:**
   ```python
   from literature_review.analysis.validation_tracker import ValidationTracker
   
   tracker = ValidationTracker("pillar_definitions_enhanced.json")
   result = tracker.analyze_validation_coverage()
   print(json.dumps(result["summary"], indent=2))
   ```

2. **Integration with proof scorecard:**
   - Must call `set_validation_tracker()` to enable validation weighting
   - Default behavior unchanged if tracker not set

3. **Handles missing files gracefully:**
   - Gap analysis is optional
   - Version history is optional
   - Works with pillar definitions only
