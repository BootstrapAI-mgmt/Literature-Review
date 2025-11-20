"""
Gap Extraction Utility for Incremental Review Mode.

Extracts open gaps from gap_analysis_report.json to target incremental analysis.
Part of INCR-W1-1: Gap Extraction Engine.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Gap:
    """Represents a research gap (sub-requirement with low completeness)."""
    
    pillar_id: str                  # e.g., "Pillar 1: Foundational Architecture"
    requirement_id: str             # e.g., "REQ-001"
    sub_requirement_id: str         # e.g., "SUB-001"
    requirement_text: str           # Full text of the requirement
    current_coverage: float         # 0.0-1.0 (completeness percentage)
    target_coverage: float          # 0.0-1.0 (desired completeness)
    gap_size: float                 # target - current (0.0-1.0)
    keywords: List[str]             # Keywords for gap-targeted search
    evidence_count: int             # Number of supporting papers
    severity: Optional[str] = None  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    
    @property
    def gap_id(self) -> str:
        """Unique identifier for this gap."""
        return f"{self.requirement_id}-{self.sub_requirement_id}"
    
    @property
    def gap_percentage(self) -> float:
        """Gap size as percentage (0-100)."""
        return self.gap_size * 100


class GapExtractor:
    """Extracts and analyzes gaps from gap analysis reports."""
    
    def __init__(
        self,
        gap_report_path: str,
        threshold: float = 0.7
    ):
        """
        Initialize gap extractor.
        
        Args:
            gap_report_path: Path to gap_analysis_report.json
            threshold: Minimum target coverage threshold (0.0-1.0).
                      Sub-requirements below this are considered gaps.
        """
        self.gap_report_path = Path(gap_report_path)
        self.threshold = threshold
        
        # Severity classification thresholds
        self.severity_thresholds = {
            "CRITICAL": 0.3,   # < 30% coverage
            "HIGH": 0.5,       # 30-50% coverage
            "MEDIUM": 0.7,     # 50-70% coverage
            "LOW": 1.0         # 70%+ coverage
        }
    
    def extract_gaps(self) -> List[Dict]:
        """
        Extract gaps from gap analysis report.
        
        Returns:
            List of gap dictionaries with structure:
            {
                'pillar_id': str,
                'requirement_id': str,
                'sub_requirement_id': str,
                'current_coverage': float,
                'target_coverage': float,
                'gap_size': float,
                'keywords': List[str],
                'evidence_count': int
            }
        """
        if not self.gap_report_path.exists():
            logger.warning(f"Gap report not found: {self.gap_report_path}")
            return []
        
        try:
            with open(self.gap_report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load gap report: {e}")
            return []
        
        gaps = []
        pillars = report.get('pillars', {})
        
        for pillar_id, pillar_data in pillars.items():
            requirements = pillar_data.get('requirements', {})
            
            for req_id, req_data in requirements.items():
                sub_requirements = req_data.get('sub_requirements', {})
                
                for sub_req_id, sub_req_data in sub_requirements.items():
                    # Get completeness (may be stored as 0-100 or 0-1)
                    completeness = sub_req_data.get('completeness_percent', 0)
                    if completeness > 1:
                        completeness = completeness / 100.0
                    
                    current_coverage = completeness
                    target_coverage = self.threshold
                    gap_size = max(0, target_coverage - current_coverage)
                    
                    # Only include if there's a gap
                    if current_coverage < target_coverage:
                        # Extract keywords from requirement text
                        req_text = sub_req_data.get('text', '')
                        keywords = self._extract_keywords(req_text)
                        
                        # Get evidence count
                        evidence = sub_req_data.get('evidence', [])
                        evidence_count = len(evidence) if isinstance(evidence, list) else 0
                        
                        gap = {
                            'pillar_id': pillar_id,
                            'requirement_id': req_id,
                            'sub_requirement_id': sub_req_id,
                            'current_coverage': current_coverage,
                            'target_coverage': target_coverage,
                            'gap_size': gap_size,
                            'keywords': keywords,
                            'evidence_count': evidence_count
                        }
                        
                        gaps.append(gap)
        
        logger.info(f"Extracted {len(gaps)} gaps (threshold: {self.threshold*100:.0f}%)")
        return gaps
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from requirement text.
        
        Simple implementation: extract meaningful words (> 3 chars).
        Future: Could use NLP for better keyword extraction.
        
        Args:
            text: Requirement text
        
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Remove common words and split
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'which', 'who', 'what', 'where',
            'when', 'why', 'how'
        }
        
        # Simple tokenization
        words = text.lower().replace(',', ' ').replace('.', ' ').split()
        keywords = [
            word for word in words
            if len(word) > 3 and word not in stopwords
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to top 10 keywords
