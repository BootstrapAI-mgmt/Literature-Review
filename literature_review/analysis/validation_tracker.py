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
    
    # Constants for alignment calculation
    PARTIAL_ALIGNMENT_SCORE = 0.3
    METHOD_ALIGNMENT_TERMS = [
        "fmri", "eeg", "recording", "simulation", "benchmark",
        "comparison", "ablation", "timing", "accuracy", "power"
    ]
    
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
        strategy = req_info.get("validation_strategy")  # Don't default to {} to detect None
        pillar_criteria = req_info.get("pillar_validation_criteria", {})
        
        # Determine if strategy is defined at requirement level
        # Empty dict {} explicitly means no strategy, even if pillar-level exists
        has_requirement_strategy = bool(
            strategy and (
                strategy.get("method") or 
                strategy.get("benchmark_protocol") or
                strategy.get("acceptance_criteria")
            )
        )
        
        # Pillar-level criteria serve as fallback only if no requirement-level strategy exists
        # and the strategy was not explicitly set (None vs empty dict {})
        has_strategy = has_requirement_strategy
        if not has_requirement_strategy and strategy is None and pillar_criteria:
            # Only use pillar-level if no strategy was defined at all (None, not empty dict)
            has_strategy = True
        
        # Ensure strategy is a dict for subsequent operations
        if strategy is None:
            strategy = {}
        
        # Get validation method details
        validation_method = strategy.get("method", "")
        benchmark_protocol = strategy.get("benchmark_protocol", "")
        acceptance_criteria = strategy.get("acceptance_criteria", "")
        
        # If no per-requirement strategy, try pillar-level criteria
        if not validation_method and pillar_criteria and has_strategy:
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
        elif alignment >= self.PARTIAL_ALIGNMENT_SCORE or len(evidence_papers) > 0:
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
            # Partial credit for having evidence without matching method
            return 0.0 if not evidence_methods else self.PARTIAL_ALIGNMENT_SCORE
        
        # Simple keyword matching for now
        method_lower = validation_method.lower()
        
        matches = 0
        total_terms = 0
        
        for term in self.METHOD_ALIGNMENT_TERMS:
            if term in method_lower:
                total_terms += 1
                for evidence_method in evidence_methods:
                    if term in evidence_method.lower():
                        matches += 1
                        break
        
        if total_terms == 0:
            return self.PARTIAL_ALIGNMENT_SCORE  # Default partial alignment
        
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
            method_preview = validation_method[:50] if validation_method else "unknown"
            gap_reason = f"Strategy defined ('{method_preview}...') but no supporting evidence"
            recommendation = f"Search for papers using: {validation_method[:100]}" if validation_method else "Search for validating evidence"
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
        
        summary = self.get_summary()
        return summary["coverage_percentage"]
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics for validation coverage.
        
        Returns:
            Dict with total_requirements, validated, partially_validated,
            unvalidated, no_strategy, coverage_percentage, strategy_definition_rate
        """
        if not self.coverage_items:
            self.analyze_validation_coverage()
        
        return self._calculate_summary()


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
