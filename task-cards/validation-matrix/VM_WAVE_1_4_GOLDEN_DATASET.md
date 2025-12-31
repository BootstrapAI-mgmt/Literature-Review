# Task Card: Golden Dataset Creation

**Task ID:** VM-W1-4  
**Wave:** 1 (Core Functional Validation)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-2  
**Blocks:** VM-W2-1, VM-W2-2, VM-W2.5-2, VM-W4-2  
**Validation IDs:** QB-01, QB-02, QB-03, QB-04, QB-05, RA-01, RA-02 (data creation)

---

## Objective

Create the actual golden dataset following the specifications from VM-W0-2. This includes human-annotated claims, expected verdicts, known gaps, recommendation quality samples, and search suggestion ground truth for output quality validation.

## Background

With the schema and guidelines defined in VM-W0-2, this task focuses on populating the golden dataset with real annotated samples. The dataset size targets are:
- 50+ annotated claims (QB-01)
- 100+ pillar mapping samples (QB-02)
- 20+ known gaps (QB-03)
- 30+ weak evidence claims (QB-04)
- 10+ recommendation quality samples (QB-05)
- 15+ search suggestion ground truth samples (RA-01, RA-02) *(Added for Wave 2.5)*
- 5+ complete output sample collections (OQ-* validation) *(Added for Wave 2.5)*

## Success Criteria

- [ ] 50 human-annotated claims created
- [ ] 100 claims with pillar mappings
- [ ] 20 known gap test cases
- [ ] 30 weak-evidence claims for false-positive testing
- [ ] 10 gaps with reference recommendations
- [ ] 15 search suggestion ground truth samples *(Added for Wave 2.5)*
- [ ] 5 validated output sample collections *(Added for Wave 2.5)*
- [ ] Dataset validates against schema
- [ ] Golden dataset loader utility works

---

## Deliverables

### 1. Golden Dataset Population Script

**File:** `tests/golden_dataset/scripts/populate_dataset.py`

```python
"""
Golden Dataset Population Script

Creates annotated samples from existing review data and manual annotation.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

# Import schema models
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import (
    AnnotatedClaim,
    EvidenceQualityAnnotation,
    ExpectedVerdict,
    KnownGap,
    RecommendationQuality,
    GoldenDataset,
    Verdict,
    ConfidenceLevel
)


class GoldenDatasetPopulator:
    """
    Populate golden dataset from various sources.
    
    Sources:
    1. Existing version history (reviewed claims)
    2. Manual annotation files
    3. Synthetic test cases
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.claims: List[AnnotatedClaim] = []
        self.verdicts: List[ExpectedVerdict] = []
        self.gaps: List[KnownGap] = []
        self.recommendations: List[RecommendationQuality] = []
        
        self.claim_counter = 0
        self.gap_counter = 0
    
    def generate_claim_id(self) -> str:
        """Generate unique claim ID."""
        self.claim_counter += 1
        return f"GD-CLM-{self.claim_counter:04d}"
    
    def generate_gap_id(self) -> str:
        """Generate unique gap ID."""
        self.gap_counter += 1
        return f"GD-GAP-{self.gap_counter:04d}"
    
    def add_annotated_claim(
        self,
        source_paper: str,
        claim_text: str,
        evidence_text: str,
        pillar: str,
        requirement: str,
        sub_requirement: str,
        mapping_rationale: str,
        verdict: str,
        verdict_rationale: str,
        confidence: str,
        strength: int,
        rigor: int,
        relevance: int,
        directness: int,
        reproducibility: int,
        evidence_rationale: str,
        test_categories: List[str],
        is_edge_case: bool = False,
        edge_case_type: Optional[str] = None,
        source_page: Optional[int] = None,
        recency_bonus: float = 0.5
    ) -> AnnotatedClaim:
        """Add an annotated claim to the dataset."""
        
        claim = AnnotatedClaim(
            claim_id=self.generate_claim_id(),
            dataset_version="1.0.0",
            source_paper=source_paper,
            source_page=source_page,
            claim_text=claim_text,
            evidence_text=evidence_text,
            correct_pillar=pillar,
            correct_requirement=requirement,
            correct_sub_requirement=sub_requirement,
            mapping_rationale=mapping_rationale,
            expected_verdict=Verdict(verdict),
            verdict_rationale=verdict_rationale,
            verdict_confidence=ConfidenceLevel(confidence),
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=strength,
                rigor_score=rigor,
                relevance_score=relevance,
                directness=directness,
                reproducibility_score=reproducibility,
                recency_bonus=recency_bonus,
                rationale=evidence_rationale
            ),
            annotator_ids=["golden_annotator_001"],
            annotation_date=datetime.now(),
            test_categories=test_categories,
            is_edge_case=is_edge_case,
            edge_case_type=edge_case_type
        )
        
        self.claims.append(claim)
        
        # Auto-generate expected verdict entry
        composite = claim.evidence_quality.composite_score
        self.verdicts.append(ExpectedVerdict(
            claim_id=claim.claim_id,
            expected_verdict=Verdict(verdict),
            expected_composite_score_range=(composite - 0.5, composite + 0.5),
            expected_strength_range=(max(1, strength - 1), min(5, strength + 1)),
            expected_relevance_range=(max(1, relevance - 1), min(5, relevance + 1)),
            true_positive_probability=0.9 if verdict == "approved" else 0.1,
            rejection_reasons=[] if verdict == "approved" else ["Insufficient evidence"]
        ))
        
        return claim
    
    def add_known_gap(
        self,
        pillar: str,
        requirement_id: str,
        sub_requirement_id: str,
        requirement_text: str,
        current_completeness: float,
        severity: str,
        database_state_file: str,
        why_is_gap: str,
        recommendation_themes: Optional[List[str]] = None,
        reference_recommendation: Optional[str] = None
    ) -> KnownGap:
        """Add a known gap to the dataset."""
        
        gap = KnownGap(
            gap_id=self.generate_gap_id(),
            dataset_version="1.0.0",
            pillar=pillar,
            requirement_id=requirement_id,
            sub_requirement_id=sub_requirement_id,
            requirement_text=requirement_text,
            current_completeness=current_completeness,
            expected_severity=severity,
            database_state_file=database_state_file,
            why_is_gap=why_is_gap,
            expected_in_report=True
        )
        
        self.gaps.append(gap)
        
        # Add recommendation if provided
        if recommendation_themes and reference_recommendation:
            self.recommendations.append(RecommendationQuality(
                gap_id=gap.gap_id,
                expected_recommendation_themes=recommendation_themes,
                expected_minimum_rating=4,
                reference_recommendation=reference_recommendation
            ))
        
        return gap
    
    def import_from_version_history(
        self,
        version_history_file: str,
        max_claims: int = 50
    ):
        """
        Import claims from existing version history.
        
        Note: These still need manual review/annotation.
        """
        if not os.path.exists(version_history_file):
            print(f"Version history not found: {version_history_file}")
            return
        
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        imported = 0
        for filename, versions in history.items():
            if imported >= max_claims:
                break
            
            for version in versions:
                review = version.get("review", {})
                requirements = review.get("Requirement(s)", [])
                
                for req in requirements:
                    if imported >= max_claims:
                        break
                    
                    # Only import judged claims
                    if req.get("status") not in ["approved", "rejected"]:
                        continue
                    
                    # Extract claim data
                    # Note: Manual review needed for mapping rationale
                    print(f"Review needed for claim from: {filename}")
                    print(f"  Claim: {req.get('extracted_claim_text', '')[:50]}...")
                    
                    imported += 1
        
        print(f"Flagged {imported} claims for manual annotation")
    
    def generate_synthetic_claims(self):
        """Generate synthetic claims for testing."""
        
        # Strong evidence claims (should be approved)
        strong_claims = [
            {
                "claim_text": "The spiking neural network achieved 95.2% ± 0.3% accuracy on MNIST classification across 10 independent trials.",
                "evidence_text": "Table 3 shows classification accuracy with standard deviation. All trials used identical initialization and training parameters.",
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "requirement": "REQ-B1.1",
                "sub_requirement": "Sub-1.1.1",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4,
                "verdict": "approved"
            },
            {
                "claim_text": "STDP learning rule produces synaptic potentiation with timing windows of ±20ms, matching biological measurements.",
                "evidence_text": "Figure 5A-C: Synaptic weight changes plotted against spike timing. Comparison with Bi & Poo (1998) data shows r=0.94 correlation.",
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "requirement": "REQ-B1.4",
                "sub_requirement": "Sub-1.4.2",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4,
                "verdict": "approved"
            },
            {
                "claim_text": "Power consumption measured at 1.2mW during inference, representing 10x reduction compared to GPU baseline.",
                "evidence_text": "Section 4.2: Power measurements using Keysight N6705C. Baseline GPU (RTX 3080) consumed 12W for equivalent task.",
                "pillar": "Pillar 2: Neuromorphic Implementation",
                "requirement": "REQ-N2.3",
                "sub_requirement": "Sub-2.3.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5,
                "verdict": "approved"
            }
        ]
        
        # Weak evidence claims (should be rejected)
        weak_claims = [
            {
                "claim_text": "Neuromorphic systems are more efficient than traditional computing.",
                "evidence_text": "As is commonly known in the field, neuromorphic approaches offer inherent efficiency advantages.",
                "pillar": "Pillar 2: Neuromorphic Implementation",
                "requirement": "REQ-N2.3",
                "sub_requirement": "Sub-2.3.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1,
                "verdict": "rejected"
            },
            {
                "claim_text": "Our architecture may improve memory consolidation.",
                "evidence_text": "Preliminary observations suggest possible improvements in retention, though more testing is needed.",
                "pillar": "Pillar 5: Memory Systems",
                "requirement": "REQ-M5.1",
                "sub_requirement": "Sub-5.1.1",
                "strength": 1, "rigor": 2, "relevance": 3, "directness": 1, "reproducibility": 1,
                "verdict": "rejected"
            },
            {
                "claim_text": "The network learns patterns efficiently.",
                "evidence_text": "Similar to [45], our approach uses efficient learning mechanisms.",
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "requirement": "REQ-B1.4",
                "sub_requirement": "Sub-1.4.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1,
                "verdict": "rejected"
            }
        ]
        
        # Borderline claims (for calibration testing)
        borderline_claims = [
            {
                "claim_text": "Initial tests show 82% classification accuracy on the DVS gesture dataset.",
                "evidence_text": "Pilot study (n=3) achieved 82% accuracy. Further validation ongoing.",
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "requirement": "REQ-B1.1",
                "sub_requirement": "Sub-1.1.2",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2,
                "verdict": "borderline"
            },
            {
                "claim_text": "The chip demonstrates sub-millisecond latency for pattern recognition.",
                "evidence_text": "Measured latency of 0.8ms ± 0.2ms across test patterns (methodology in supplementary).",
                "pillar": "Pillar 2: Neuromorphic Implementation",
                "requirement": "REQ-N2.1",
                "sub_requirement": "Sub-2.1.1",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 3,
                "verdict": "borderline"
            }
        ]
        
        # Add strong claims
        for i, claim_data in enumerate(strong_claims):
            self.add_annotated_claim(
                source_paper=f"synthetic_strong_{i+1}.pdf",
                claim_text=claim_data["claim_text"],
                evidence_text=claim_data["evidence_text"],
                pillar=claim_data["pillar"],
                requirement=claim_data["requirement"],
                sub_requirement=claim_data["sub_requirement"],
                mapping_rationale="Directly addresses requirement with quantitative evidence",
                verdict=claim_data["verdict"],
                verdict_rationale="Strong quantitative evidence meeting all criteria",
                confidence="high",
                strength=claim_data["strength"],
                rigor=claim_data["rigor"],
                relevance=claim_data["relevance"],
                directness=claim_data["directness"],
                reproducibility=claim_data["reproducibility"],
                evidence_rationale="Clear methodology with statistical measures",
                test_categories=["precision", "judge_accuracy", "pillar_mapping"]
            )
        
        # Add weak claims
        for i, claim_data in enumerate(weak_claims):
            self.add_annotated_claim(
                source_paper=f"synthetic_weak_{i+1}.pdf",
                claim_text=claim_data["claim_text"],
                evidence_text=claim_data["evidence_text"],
                pillar=claim_data["pillar"],
                requirement=claim_data["requirement"],
                sub_requirement=claim_data["sub_requirement"],
                mapping_rationale="Topic matches but evidence is insufficient",
                verdict=claim_data["verdict"],
                verdict_rationale="Insufficient evidence - no quantitative data or speculation",
                confidence="high",
                strength=claim_data["strength"],
                rigor=claim_data["rigor"],
                relevance=claim_data["relevance"],
                directness=claim_data["directness"],
                reproducibility=claim_data["reproducibility"],
                evidence_rationale="Lacks methodology, data, or concrete claims",
                test_categories=["recall", "false_approval_prevention"]
            )
        
        # Add borderline claims
        for i, claim_data in enumerate(borderline_claims):
            self.add_annotated_claim(
                source_paper=f"synthetic_borderline_{i+1}.pdf",
                claim_text=claim_data["claim_text"],
                evidence_text=claim_data["evidence_text"],
                pillar=claim_data["pillar"],
                requirement=claim_data["requirement"],
                sub_requirement=claim_data["sub_requirement"],
                mapping_rationale="Relevant topic with mixed evidence quality",
                verdict=claim_data["verdict"],
                verdict_rationale="Borderline case - composite score near threshold",
                confidence="medium",
                strength=claim_data["strength"],
                rigor=claim_data["rigor"],
                relevance=claim_data["relevance"],
                directness=claim_data["directness"],
                reproducibility=claim_data["reproducibility"],
                evidence_rationale="Some data present but methodology concerns",
                test_categories=["calibration", "borderline"],
                is_edge_case=True,
                edge_case_type="borderline_evidence"
            )
    
    def generate_synthetic_gaps(self):
        """Generate synthetic gaps for testing."""
        
        gaps = [
            {
                "pillar": "Pillar 2: Neuromorphic Implementation",
                "requirement_id": "REQ-N2.2",
                "sub_requirement_id": "Sub-2.2.3",
                "requirement_text": "Hardware implementation of temporal coding with sub-ms precision",
                "completeness": 15.0,
                "severity": "CRITICAL",
                "why": "No papers in database address temporal coding hardware with required precision",
                "themes": ["temporal coding", "hardware implementation", "spike timing", "precision"],
                "recommendation": "Search for papers on precise temporal coding in neuromorphic chips, particularly Intel Loihi or custom ASIC implementations."
            },
            {
                "pillar": "Pillar 5: Memory Systems",
                "requirement_id": "REQ-M5.2",
                "sub_requirement_id": "Sub-5.2.1",
                "requirement_text": "Working memory implementation with 7±2 item capacity",
                "completeness": 25.0,
                "severity": "HIGH",
                "why": "Limited coverage of working memory capacity constraints in neuromorphic systems",
                "themes": ["working memory", "capacity limit", "neural implementation"],
                "recommendation": "Look for computational models of prefrontal cortex working memory with capacity constraints."
            },
            {
                "pillar": "Pillar 3: Skill Acquisition",
                "requirement_id": "REQ-S3.1",
                "sub_requirement_id": "Sub-3.1.2",
                "requirement_text": "Progressive automatization of learned skills",
                "completeness": 40.0,
                "severity": "MEDIUM",
                "why": "Some coverage but lacks integration with motor learning literature",
                "themes": ["skill learning", "automatization", "motor cortex", "procedural memory"],
                "recommendation": "Expand search to motor learning and basal ganglia literature for skill automatization."
            }
        ]
        
        for gap_data in gaps:
            self.add_known_gap(
                pillar=gap_data["pillar"],
                requirement_id=gap_data["requirement_id"],
                sub_requirement_id=gap_data["sub_requirement_id"],
                requirement_text=gap_data["requirement_text"],
                current_completeness=gap_data["completeness"],
                severity=gap_data["severity"],
                database_state_file=f"gap_states/{gap_data['sub_requirement_id']}.json",
                why_is_gap=gap_data["why"],
                recommendation_themes=gap_data["themes"],
                reference_recommendation=gap_data["recommendation"]
            )
    
    def save(self, filename: str = "golden_dataset.json"):
        """Save the golden dataset to file."""
        
        dataset = GoldenDataset(
            version="1.0.0",
            created_date=datetime.now(),
            last_updated=datetime.now(),
            description="Golden dataset for Literature Review validation testing",
            annotated_claims=self.claims,
            expected_verdicts=self.verdicts,
            known_gaps=self.gaps,
            recommendation_quality=self.recommendations
        )
        
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset.model_dump(mode='json'), f, indent=2, default=str)
        
        print(f"Saved golden dataset to: {output_file}")
        print(f"  Claims: {len(self.claims)}")
        print(f"  Verdicts: {len(self.verdicts)}")
        print(f"  Gaps: {len(self.gaps)}")
        print(f"  Recommendations: {len(self.recommendations)}")
        
        return output_file


def main():
    """Generate the golden dataset."""
    output_dir = Path(__file__).parent.parent / "data"
    
    populator = GoldenDatasetPopulator(output_dir)
    
    # Generate synthetic claims
    populator.generate_synthetic_claims()
    
    # Generate synthetic gaps
    populator.generate_synthetic_gaps()
    
    # Save dataset
    populator.save()


if __name__ == "__main__":
    main()
```

### 2. Annotation Template

**File:** `tests/golden_dataset/templates/annotation_template.json`

```json
{
  "_instructions": "Fill in this template for each claim to be added to the golden dataset",
  
  "source_paper": "REQUIRED: filename.pdf",
  "source_page": "OPTIONAL: page number",
  "source_section": "OPTIONAL: section name",
  
  "claim_text": "REQUIRED: The exact claim text from the paper",
  "evidence_text": "REQUIRED: The supporting evidence text",
  
  "correct_pillar": "REQUIRED: Full pillar name (e.g., 'Pillar 1: Biological Stimulus-Response')",
  "correct_requirement": "REQUIRED: Requirement ID (e.g., 'REQ-B1.1')",
  "correct_sub_requirement": "REQUIRED: Sub-requirement ID (e.g., 'Sub-1.1.1')",
  "mapping_rationale": "REQUIRED: Why this claim maps to this requirement",
  
  "expected_verdict": "REQUIRED: 'approved', 'rejected', or 'borderline'",
  "verdict_rationale": "REQUIRED: Why this verdict is expected",
  "verdict_confidence": "REQUIRED: 'high', 'medium', or 'low'",
  
  "evidence_quality": {
    "strength_score": "REQUIRED: 1-5",
    "rigor_score": "REQUIRED: 1-5",
    "relevance_score": "REQUIRED: 1-5",
    "directness": "REQUIRED: 1-3",
    "reproducibility_score": "REQUIRED: 1-5",
    "recency_bonus": "OPTIONAL: 0.0-1.0 (default 0.5)",
    "rationale": "REQUIRED: Justification for scores"
  },
  
  "annotator_id": "REQUIRED: Your annotator ID",
  
  "test_categories": "REQUIRED: List from [precision, recall, judge_accuracy, pillar_mapping, calibration, false_approval_prevention, borderline]",
  
  "is_edge_case": "OPTIONAL: true/false",
  "edge_case_type": "OPTIONAL: 'borderline_evidence', 'ambiguous_mapping', 'multi_pillar', etc."
}
```

---

## Implementation Steps

### Step 1: Create Population Script (2 hours)
1. Implement `GoldenDatasetPopulator` class
2. Add claim and gap generation methods
3. Create save/export functionality

### Step 2: Generate Synthetic Data (2 hours)
1. Create 20+ strong evidence claims
2. Create 20+ weak evidence claims
3. Create 10+ borderline claims
4. Create 20+ known gaps

### Step 3: Manual Annotation (3 hours)
1. Review existing version history claims
2. Apply annotation template
3. Verify quality and consistency

### Step 4: Validation & Integration (1 hour)
1. Validate dataset against schema
2. Test loader utility
3. Run sample queries

---

## Testing

```bash
# Generate the golden dataset
python tests/golden_dataset/scripts/populate_dataset.py

# Validate the dataset
python -c "from tests.golden_dataset.loader import GoldenDatasetLoader; loader = GoldenDatasetLoader(); print(loader.load().stats)"

# Run validation tests with golden dataset
pytest tests/validation/ -k "golden" -v
```

---

## Acceptance Criteria Checklist

- [ ] 50+ annotated claims in dataset
- [ ] 20+ approved claims (QB-01)
- [ ] 20+ rejected claims (QB-04)
- [ ] 10+ borderline claims (calibration)
- [ ] 100+ pillar mappings (QB-02)
- [ ] 20+ known gaps (QB-03)
- [ ] 10+ recommendation samples (QB-05)
- [ ] Dataset validates against schema
- [ ] Loader utility functional
- [ ] Documentation complete

---

## Related Tasks

- **Depends on:** VM-W0-2 (Golden Dataset Specification)
- **Enables:** VM-W2-1, VM-W2-2, VM-W4-2
- **Parallel:** VM-W1-1, VM-W1-2, VM-W1-3

---

## Notes

- Start with synthetic data for initial testing
- Expand with real paper annotations over time
- Consider crowdsourcing annotation for larger datasets
- Version the dataset and track changes
