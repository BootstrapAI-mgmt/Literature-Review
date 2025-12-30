"""
Domain Stakeholder Extractor

Extracts domain stakeholder impacts from research literature.
Captures explicit statements linking research gaps to affected
stakeholders as stated in papers.
"""

import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from literature_review.models.domain_stakeholder import (
    DomainStakeholder,
    LiteratureStakeholderImpact,
    StakeholderCategory,
    generate_impact_id
)
from literature_review.reviewers.prompts.stakeholder_extraction_prompt import (
    format_stakeholder_extraction_prompt,
    parse_extraction_response,
    MIN_CONFIDENCE_THRESHOLD
)

logger = logging.getLogger(__name__)


# Stakeholder normalization mappings
STAKEHOLDER_ALIASES = {
    # Researchers
    "neuroscientists": "neuroscientists",
    "neuroscience researchers": "neuroscientists",
    "neural network researchers": "neural network researchers",
    "researchers": "researchers",
    "research scientists": "researchers",
    "academic researchers": "researchers",
    "computational neuroscientists": "computational neuroscientists",
    
    # Engineers
    "hardware engineers": "hardware engineers",
    "chip designers": "hardware engineers",
    "neuromorphic engineers": "hardware engineers",
    "software engineers": "software engineers",
    "system designers": "system designers",
    "embedded systems engineers": "embedded systems engineers",
    
    # Clinicians
    "clinical researchers": "clinical researchers",
    "clinicians": "clinicians",
    "medical researchers": "medical researchers",
    "physicians": "clinicians",
    
    # Practitioners
    "industry practitioners": "industry practitioners",
    "practitioners": "practitioners",
    
    # Others
    "data scientists": "data scientists",
    "machine learning engineers": "machine learning engineers",
}


class DomainStakeholderExtractor:
    """
    Extract domain stakeholder impacts from research literature.
    
    Captures explicit statements linking research gaps to affected
    stakeholders as stated in papers.
    
    Attributes:
        gap_analysis: Loaded gap analysis for linkage
        impacts: List of extracted stakeholder impacts
        stakeholders: Dict mapping stakeholder type to DomainStakeholder
    """
    
    def __init__(
        self,
        gap_analysis_path: Optional[str] = None,
        similarity_threshold: float = 0.8
    ):
        """
        Initialize with gap analysis for linkage.
        
        Args:
            gap_analysis_path: Path to gap analysis JSON file
            similarity_threshold: Threshold for gap linkage (0-1)
        """
        self.gap_analysis = {}
        if gap_analysis_path:
            self.gap_analysis = self._load_gap_analysis(gap_analysis_path)
        
        self.similarity_threshold = similarity_threshold
        self.impacts: List[LiteratureStakeholderImpact] = []
        self.stakeholders: Dict[str, DomainStakeholder] = {}
        self._impact_sequence = 0
    
    def _load_gap_analysis(self, gap_analysis_path: str) -> Dict:
        """Load gap analysis from JSON file."""
        try:
            path = Path(gap_analysis_path)
            if path.exists():
                with open(path, "r") as f:
                    data = json.load(f)
                logger.info(f"Loaded gap analysis from {gap_analysis_path}")
                return data
            else:
                logger.warning(f"Gap analysis file not found: {gap_analysis_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading gap analysis: {e}")
            return {}
    
    def _normalize_stakeholder(self, stakeholder_type: str) -> str:
        """
        Normalize stakeholder type to canonical form.
        
        Args:
            stakeholder_type: Raw stakeholder type from paper
            
        Returns:
            Normalized stakeholder type
        """
        # Lowercase for matching
        lower = stakeholder_type.lower().strip()
        
        # Check aliases
        if lower in STAKEHOLDER_ALIASES:
            return STAKEHOLDER_ALIASES[lower]
        
        return stakeholder_type
    
    def _categorize_stakeholder(self, stakeholder_type: str) -> StakeholderCategory:
        """
        Categorize stakeholder into broad category.
        
        Args:
            stakeholder_type: Stakeholder type
            
        Returns:
            StakeholderCategory enum
        """
        lower = stakeholder_type.lower()
        
        if any(term in lower for term in ["researcher", "scientist", "academic"]):
            return StakeholderCategory.RESEARCHER
        elif any(term in lower for term in ["engineer", "designer", "developer"]):
            return StakeholderCategory.ENGINEER
        elif any(term in lower for term in ["clinician", "physician", "medical", "clinical"]):
            return StakeholderCategory.CLINICIAN
        elif any(term in lower for term in ["practitioner", "industry"]):
            return StakeholderCategory.PRACTITIONER
        elif any(term in lower for term in ["policy", "regulator", "government"]):
            return StakeholderCategory.POLICY_MAKER
        elif any(term in lower for term in ["user", "patient", "consumer"]):
            return StakeholderCategory.END_USER
        else:
            return StakeholderCategory.OTHER
    
    def extract_from_response(
        self,
        response: List[Dict],
        filename: str
    ) -> List[LiteratureStakeholderImpact]:
        """
        Extract stakeholder impacts from LLM response.
        
        Args:
            response: Parsed JSON response from LLM
            filename: Source paper filename
            
        Returns:
            List of LiteratureStakeholderImpact objects
        """
        # Validate and parse response
        validated = parse_extraction_response(response)
        
        impacts = []
        for item in validated:
            self._impact_sequence += 1
            
            # Normalize stakeholder
            raw_stakeholder = item["affected_stakeholder"]
            normalized = self._normalize_stakeholder(raw_stakeholder)
            
            # Get or determine category
            if item.get("stakeholder_category"):
                try:
                    category = StakeholderCategory(item["stakeholder_category"])
                except ValueError:
                    category = self._categorize_stakeholder(normalized)
            else:
                category = self._categorize_stakeholder(normalized)
            
            # Generate gap ID based on description
            gap_id = self._generate_gap_id(item["gap_description"])
            
            # Link to existing gap analysis if possible
            linked_gap_id = self.link_to_gap_analysis(item["gap_description"])
            if linked_gap_id:
                gap_id = linked_gap_id
            
            # Generate unique impact ID
            impact_id = generate_impact_id(
                filename,
                gap_id,
                normalized,
                self._impact_sequence
            )
            
            # Create impact
            impact = LiteratureStakeholderImpact(
                impact_id=impact_id,
                gap_id=gap_id,
                gap_description=item["gap_description"],
                affected_stakeholder=normalized,
                stakeholder_category=category,
                impact_statement=item["impact_statement"],
                source_quote=item.get("source_quote"),
                source_paper=filename,
                paper_section=item.get("paper_section"),
                extraction_confidence=item.get("confidence", 0.8)
            )
            
            impacts.append(impact)
            self.impacts.append(impact)
            
            # Update stakeholders registry
            self._update_stakeholder_registry(normalized, category, filename, item)
        
        logger.info(f"Extracted {len(impacts)} stakeholder impacts from {filename}")
        return impacts
    
    def _update_stakeholder_registry(
        self,
        stakeholder_type: str,
        category: StakeholderCategory,
        filename: str,
        item: Dict
    ) -> None:
        """Update the stakeholders registry with new stakeholder info."""
        if stakeholder_type not in self.stakeholders:
            self.stakeholders[stakeholder_type] = DomainStakeholder(
                stakeholder_type=stakeholder_type,
                category=category,
                description=item.get("impact_statement", ""),
                source_papers=[filename]
            )
        else:
            # Add paper to existing stakeholder
            if filename not in self.stakeholders[stakeholder_type].source_papers:
                self.stakeholders[stakeholder_type].source_papers.append(filename)
    
    def _generate_gap_id(self, gap_description: str) -> str:
        """Generate a gap ID from description hash."""
        hash_val = hashlib.md5(gap_description.encode()).hexdigest()[:8]
        return f"GAP-{hash_val}"
    
    def link_to_gap_analysis(
        self,
        gap_description: str
    ) -> Optional[str]:
        """
        Attempt to link extracted impact to existing gap analysis.
        
        Uses simple text matching. For production, consider using
        embedding similarity.
        
        Args:
            gap_description: Gap description from paper
            
        Returns:
            Gap ID if found, None otherwise
        """
        if not self.gap_analysis:
            return None
        
        gap_lower = gap_description.lower()
        
        # Search through gap analysis structure
        for pillar_name, pillar_data in self.gap_analysis.items():
            if not isinstance(pillar_data, dict):
                continue
                
            analysis = pillar_data.get("analysis", {})
            for req_key, req_data in analysis.items():
                if not isinstance(req_data, dict):
                    continue
                    
                for sub_req_key, sub_req_data in req_data.items():
                    if not isinstance(sub_req_data, dict):
                        continue
                    
                    gap_text = sub_req_data.get("gap_analysis", "").lower()
                    
                    # Simple overlap check
                    overlap = self._calculate_text_overlap(gap_lower, gap_text)
                    if overlap > self.similarity_threshold:
                        return f"{req_key}-{sub_req_key}"
        
        return None
    
    def _calculate_text_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate simple word overlap ratio between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Overlap ratio (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def check_gap_resolution(
        self,
        new_paper: str,
        new_paper_claims: List[Dict]
    ) -> List[str]:
        """
        Check if new paper resolves any tracked gaps.
        
        Args:
            new_paper: Filename of new paper
            new_paper_claims: Claims extracted from new paper
            
        Returns:
            List of resolved impact IDs
        """
        resolved_ids = []
        current_date = datetime.now().isoformat()
        
        for claim in new_paper_claims:
            claim_text = claim.get("claim_summary", "").lower()
            
            for impact in self.impacts:
                if impact.gap_filled:
                    continue
                
                # Check if claim addresses the gap
                gap_lower = impact.gap_description.lower()
                overlap = self._calculate_text_overlap(claim_text, gap_lower)
                
                if overlap > 0.5:  # Lower threshold for resolution
                    impact.mark_resolved(new_paper, current_date)
                    resolved_ids.append(impact.impact_id)
                    logger.info(
                        f"Gap '{impact.impact_id}' resolved by {new_paper}"
                    )
        
        return resolved_ids
    
    def _group_by_stakeholder(self) -> Dict[str, List[Dict]]:
        """Group impacts by stakeholder type."""
        grouped = defaultdict(list)
        
        for impact in self.impacts:
            grouped[impact.affected_stakeholder].append({
                "impact_id": impact.impact_id,
                "gap_description": impact.gap_description,
                "impact_statement": impact.impact_statement,
                "source_paper": impact.source_paper,
                "gap_filled": impact.gap_filled
            })
        
        return dict(grouped)
    
    def _get_open_gaps_by_stakeholder(self) -> Dict[str, int]:
        """Get count of open gaps per stakeholder."""
        counts = defaultdict(int)
        
        for impact in self.impacts:
            if not impact.gap_filled:
                counts[impact.affected_stakeholder] += 1
        
        return dict(counts)
    
    def generate_report(self) -> Dict:
        """
        Generate stakeholder impact report.
        
        Returns:
            Report dictionary with summary, stakeholders, and impacts
        """
        return {
            "report_type": "literature_domain_stakeholder_impacts",
            "description": "Stakeholder impacts as explicitly stated in research literature",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_impacts": len(self.impacts),
                "unique_stakeholders": len(self.stakeholders),
                "open_impacts": len([i for i in self.impacts if not i.gap_filled]),
                "resolved_impacts": len([i for i in self.impacts if i.gap_filled])
            },
            "stakeholders": {
                k: {
                    **v.to_dict(),
                    "impact_count": len([
                        i for i in self.impacts 
                        if i.affected_stakeholder == k
                    ])
                }
                for k, v in self.stakeholders.items()
            },
            "impacts_by_stakeholder": self._group_by_stakeholder(),
            "open_gaps_by_stakeholder": self._get_open_gaps_by_stakeholder(),
            "all_impacts": [i.to_dict() for i in self.impacts]
        }
    
    def save_report(self, output_path: str) -> None:
        """
        Save literature stakeholder impacts to file.
        
        Args:
            output_path: Path to output JSON file
        """
        report = self.generate_report()
        
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved stakeholder impact report to {output_path}")
    
    def load_existing(self, input_path: str) -> None:
        """
        Load existing stakeholder impacts from file.
        
        Args:
            input_path: Path to existing JSON file
        """
        try:
            path = Path(input_path)
            if not path.exists():
                logger.info(f"No existing report at {input_path}")
                return
            
            with open(path, "r") as f:
                data = json.load(f)
            
            # Load impacts
            for impact_data in data.get("all_impacts", []):
                impact = LiteratureStakeholderImpact.from_dict(impact_data)
                self.impacts.append(impact)
            
            # Load stakeholders
            for stakeholder_type, stakeholder_data in data.get("stakeholders", {}).items():
                self.stakeholders[stakeholder_type] = DomainStakeholder.from_dict(
                    stakeholder_data
                )
            
            # Update sequence counter
            self._impact_sequence = len(self.impacts)
            
            logger.info(
                f"Loaded {len(self.impacts)} existing impacts from {input_path}"
            )
            
        except Exception as e:
            logger.error(f"Error loading existing report: {e}")
    
    def get_impacts_for_stakeholder(
        self,
        stakeholder_type: str
    ) -> List[LiteratureStakeholderImpact]:
        """
        Get all impacts for a specific stakeholder type.
        
        Args:
            stakeholder_type: Stakeholder type to filter by
            
        Returns:
            List of impacts affecting this stakeholder
        """
        normalized = self._normalize_stakeholder(stakeholder_type)
        return [
            i for i in self.impacts 
            if self._normalize_stakeholder(i.affected_stakeholder) == normalized
        ]
    
    def get_open_impacts(self) -> List[LiteratureStakeholderImpact]:
        """Get all unresolved impacts."""
        return [i for i in self.impacts if not i.gap_filled]
    
    def get_resolved_impacts(self) -> List[LiteratureStakeholderImpact]:
        """Get all resolved impacts."""
        return [i for i in self.impacts if i.gap_filled]
