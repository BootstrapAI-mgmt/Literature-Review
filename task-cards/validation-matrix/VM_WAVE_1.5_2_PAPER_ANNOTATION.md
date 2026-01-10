# Task Card: Paper Annotation for Golden Dataset

**Task ID:** VM-W1.5-2  
**Wave:** 1.5 (Golden Dataset Enhancement)  
**Priority:** HIGH  
**Estimated Effort:** 20 hours  
**Status:** Not Started  
**Dependencies:** VM-W1-4, VM-W1.5-1  
**Blocks:** VM-W2-1, VM-W2-2, VM-W4-2  
**Validation IDs:** QB-01, QB-02, QB-03, QB-04, QB-05 (real data)

---

## Objective

Annotate claims, gaps, and recommendations from the 80+ open access papers sourced in VM-W1.5-1. This creates a high-quality golden dataset grounded in real academic literature, enabling rigorous cross-domain validation of the literature review system.

## Background

Synthetic claims (VM-W1-4) bootstrap the golden dataset, but real annotations are essential for:
1. **Authentic claim structures** - Real academic language, hedging, caveats
2. **Natural evidence quality distribution** - Not artificially balanced
3. **Cross-domain generalization** - Validates system beyond training domain
4. **Edge case discovery** - Real papers contain unexpected patterns
5. **Benchmark credibility** - Industry-standard approach to validation

**Annotation Targets:**
- 400-640 annotated claims (5-8 per paper × 80 papers)
- 160+ known gaps (2+ per paper)
- 80+ recommendation quality samples (1+ per paper)

---

## Success Criteria

- [ ] 400+ claims annotated from real papers
- [ ] Each paper has 5-8 annotated claims
- [ ] Mix: ~50% approved, ~30% rejected, ~20% borderline
- [ ] 160+ known gaps identified
- [ ] 80+ recommendation quality samples
- [ ] All 8 domains represented equally (10+ papers each)
- [ ] Inter-annotator agreement ≥80% (if multiple annotators)
- [ ] Annotations validate against golden dataset schema

---

## Annotation Workflow

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ANNOTATION PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ 1. Paper │ -> │ 2. Claim │ -> │ 3. Score │ -> │ 4. Map │ │
│  │   Read   │    │  Extract │    │ Evidence │    │ Pillar │ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ 5. Gaps  │ -> │ 6. Recs  │ -> │ 7. Review│              │
│  │ Identify │    │  Create  │    │ & Export │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Paper Reading (Pre-Annotation)

Before annotation, reviewer must:
1. Read paper abstract and introduction
2. Skim methods and results sections
3. Identify 5-8 candidate claims with evidence
4. Note paper's overall evidence quality level

### Step 2: Claim Extraction

For each claim, capture:

| Field | Description | Example |
|-------|-------------|---------|
| `claim_text` | Exact text or paraphrase | "Our SNN achieved 94.2% accuracy on MNIST" |
| `evidence_text` | Supporting evidence | "Table 3 shows accuracy across datasets..." |
| `source_page` | Page number | 7 |
| `claim_type` | quantitative/qualitative | quantitative |
| `hedging_level` | none/low/moderate/high | low |

### Step 3: Evidence Quality Scoring

Score each claim's evidence (1-5 scale):

| Dimension | 1 (Poor) | 3 (Adequate) | 5 (Excellent) |
|-----------|----------|--------------|---------------|
| **Strength** | Anecdotal | Single study | Multi-study meta |
| **Rigor** | No methodology | Basic methods | Rigorous methodology |
| **Relevance** | Tangential | Related | Directly applicable |
| **Directness** | Heavily inferred | Moderate inference | Direct support |
| **Reproducibility** | No details | Partial details | Full reproduction |

### Step 4: Pillar Mapping

Map each claim to the pillar hierarchy:

```yaml
correct_pillar: "Technology"
correct_requirement: "Scalability"  
correct_sub_requirement: "Energy Efficiency"
mapping_rationale: "Claim addresses power consumption which maps to energy efficiency metrics under scalability."
```

### Step 5: Gap Identification

For each paper, identify 2+ gaps:

| Field | Description |
|-------|-------------|
| `gap_pillar` | Which pillar has insufficient coverage |
| `gap_requirement` | Specific requirement lacking |
| `current_completeness` | Estimated % (0.0-1.0) |
| `severity` | critical/major/moderate/minor |
| `why_is_gap` | Explanation of missing evidence |

### Step 6: Recommendation Creation

For each gap, create quality recommendation:

| Field | Description |
|-------|-------------|
| `gap_id` | Link to identified gap |
| `reference_recommendation` | Gold-standard recommendation text |
| `recommendation_themes` | Keywords for matching |
| `recommendation_specificity` | generic/moderate/specific |
| `has_search_terms` | true/false |

### Step 7: Review & Export

1. Self-review annotations for consistency
2. Run schema validation
3. Export to golden dataset format

---

## Deliverables

### 1. Annotation Interface Script

**File:** `tests/golden_dataset/scripts/annotate_paper.py`

```python
"""
Paper Annotation Interface

Provides structured workflow for annotating papers from the registry.
Outputs to golden dataset schema format.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import (
    AnnotatedClaim, ExpectedVerdict, KnownGap, 
    RecommendationQuality, EvidenceQualityAnnotation,
    Verdict, ConfidenceLevel
)


class PaperAnnotator:
    """Interactive paper annotation workflow."""
    
    def __init__(self, paper_id: str, annotator_id: str):
        self.paper_id = paper_id
        self.annotator_id = annotator_id
        self.claims: List[AnnotatedClaim] = []
        self.gaps: List[KnownGap] = []
        self.recommendations: List[RecommendationQuality] = []
        self.claim_counter = 0
    
    def add_claim(
        self,
        claim_text: str,
        evidence_text: str,
        source_page: int,
        pillar: str,
        requirement: str,
        sub_requirement: str,
        mapping_rationale: str,
        verdict: str,  # approved/rejected/borderline
        verdict_rationale: str,
        confidence: str,  # high/medium/low
        strength: int,  # 1-5
        rigor: int,  # 1-5
        relevance: int,  # 1-5
        directness: int,  # 1-5
        reproducibility: int,  # 1-5
        recency_bonus: float = 0.5,
        is_edge_case: bool = False,
        edge_case_type: Optional[str] = None
    ) -> AnnotatedClaim:
        """Add annotated claim from paper."""
        self.claim_counter += 1
        claim_id = f"{self.paper_id}-CLM-{self.claim_counter:03d}"
        
        # Determine test categories based on scores
        test_categories = self._infer_test_categories(
            verdict, strength, confidence
        )
        
        claim = AnnotatedClaim(
            claim_id=claim_id,
            dataset_version="1.0.0",
            source_paper=self.paper_id,
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
                rationale=f"Evidence from {self.paper_id} page {source_page}"
            ),
            annotator_ids=[self.annotator_id],
            annotation_date=datetime.now(),
            test_categories=test_categories,
            is_edge_case=is_edge_case,
            edge_case_type=edge_case_type
        )
        
        self.claims.append(claim)
        return claim
    
    def _infer_test_categories(
        self, verdict: str, strength: int, confidence: str
    ) -> List[str]:
        """Infer test categories from annotation."""
        categories = ["real_paper"]
        
        if verdict == "approved":
            categories.append("true_positive")
            if strength >= 4:
                categories.append("strong_evidence")
        elif verdict == "rejected":
            categories.append("true_negative")
            if strength <= 2:
                categories.append("weak_evidence")
        else:  # borderline
            categories.append("calibration")
            categories.append("borderline")
        
        if confidence == "low":
            categories.append("uncertain")
        
        return categories
    
    def add_gap(
        self,
        pillar: str,
        requirement_id: str,
        sub_requirement_id: str,
        requirement_text: str,
        current_completeness: float,
        severity: str,
        why_is_gap: str,
        recommendation_themes: Optional[List[str]] = None
    ) -> KnownGap:
        """Add known gap from paper analysis."""
        gap_id = f"{self.paper_id}-GAP-{len(self.gaps) + 1:03d}"
        
        gap = KnownGap(
            gap_id=gap_id,
            dataset_version="1.0.0",
            pillar=pillar,
            requirement_id=requirement_id,
            sub_requirement_id=sub_requirement_id,
            requirement_text=requirement_text,
            current_completeness=current_completeness,
            severity=severity,
            database_state_file=f"state_{self.paper_id}.json",
            why_is_gap=why_is_gap,
            recommendation_themes=recommendation_themes or [],
            annotator_id=self.annotator_id,
            annotation_date=datetime.now()
        )
        
        self.gaps.append(gap)
        return gap
    
    def add_recommendation(
        self,
        gap_id: str,
        reference_recommendation: str,
        themes: List[str],
        specificity: str = "moderate"
    ) -> RecommendationQuality:
        """Add recommendation quality sample."""
        rec_id = f"{self.paper_id}-REC-{len(self.recommendations) + 1:03d}"
        
        rec = RecommendationQuality(
            recommendation_id=rec_id,
            gap_id=gap_id,
            reference_recommendation=reference_recommendation,
            recommendation_themes=themes,
            expected_action_items=self._extract_action_items(reference_recommendation),
            specificity_level=specificity,
            has_search_terms=any(t in reference_recommendation.lower() 
                                for t in ["search", "review", "investigate"]),
            annotator_id=self.annotator_id
        )
        
        self.recommendations.append(rec)
        return rec
    
    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items from recommendation text."""
        # Simple heuristic: sentences starting with action verbs
        action_verbs = ["Conduct", "Review", "Analyze", "Evaluate", 
                       "Investigate", "Search", "Compare", "Assess"]
        items = []
        for sentence in text.split(". "):
            if any(sentence.strip().startswith(v) for v in action_verbs):
                items.append(sentence.strip())
        return items[:3]  # Max 3 action items
    
    def export(self, output_path: Path) -> dict:
        """Export annotations to JSON."""
        output = {
            "paper_id": self.paper_id,
            "annotator_id": self.annotator_id,
            "annotation_date": datetime.now().isoformat(),
            "claims": [c.model_dump(mode="json") for c in self.claims],
            "gaps": [g.model_dump(mode="json") for g in self.gaps],
            "recommendations": [r.model_dump(mode="json") for r in self.recommendations],
            "statistics": {
                "total_claims": len(self.claims),
                "approved": sum(1 for c in self.claims if c.expected_verdict == Verdict.approved),
                "rejected": sum(1 for c in self.claims if c.expected_verdict == Verdict.rejected),
                "borderline": sum(1 for c in self.claims if c.expected_verdict == Verdict.borderline),
                "total_gaps": len(self.gaps),
                "total_recommendations": len(self.recommendations)
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"Exported: {len(self.claims)} claims, {len(self.gaps)} gaps, "
              f"{len(self.recommendations)} recommendations to {output_path}")
        
        return output


def main():
    """CLI for paper annotation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Annotate papers for golden dataset")
    parser.add_argument("command", choices=["start", "status", "merge", "validate"])
    parser.add_argument("--paper-id", help="Paper ID to annotate")
    parser.add_argument("--annotator", default="annotator_001", help="Annotator ID")
    parser.add_argument("--output-dir", default="tests/golden_dataset/annotations")
    
    args = parser.parse_args()
    
    if args.command == "start":
        if not args.paper_id:
            print("Error: --paper-id required for start command")
            return
        
        annotator = PaperAnnotator(args.paper_id, args.annotator)
        print(f"Started annotation session for {args.paper_id}")
        print("Use the PaperAnnotator methods to add claims, gaps, recommendations")
        print(f"Export with: annotator.export(Path('{args.output_dir}/{args.paper_id}.json'))")
    
    elif args.command == "status":
        # Show annotation progress
        annotations_dir = Path(args.output_dir)
        if annotations_dir.exists():
            files = list(annotations_dir.glob("*.json"))
            print(f"Annotations completed: {len(files)}")
            for f in files:
                with open(f) as fh:
                    data = json.load(fh)
                    stats = data.get("statistics", {})
                    print(f"  {f.stem}: {stats.get('total_claims', 0)} claims, "
                          f"{stats.get('total_gaps', 0)} gaps")
        else:
            print("No annotations found.")
    
    elif args.command == "merge":
        # Merge all annotations into golden dataset
        print("Merging annotations into golden dataset...")
        # Implementation: iterate annotation files, merge into golden_dataset.json
    
    elif args.command == "validate":
        # Validate annotations against schema
        print("Validating annotations...")
        # Implementation: load each annotation, validate against Pydantic models


if __name__ == "__main__":
    main()
```

### 2. Annotation Guidelines Document

**File:** `tests/golden_dataset/ANNOTATION_GUIDELINES.md`

```markdown
# Golden Dataset Annotation Guidelines

## Overview

This document provides guidelines for annotating papers in the golden dataset.
Consistent annotation is critical for benchmark validity.

## Claim Selection Criteria

### What IS a claim:
- Quantitative assertion with numerical evidence
- Performance comparison with baseline
- Experimental result with methodology
- Statistical finding with confidence

### What is NOT a claim:
- Background information or definitions
- Future work statements
- Opinions without evidence
- Related work summaries

## Evidence Quality Scoring Guide

### Strength (1-5)
| Score | Description | Example |
|-------|-------------|---------|
| 1 | Anecdotal/opinion | "We believe this approach is better" |
| 2 | Single observation | "In one experiment, we saw..." |
| 3 | Single study results | "Our study shows 94% accuracy" |
| 4 | Multiple studies | "Across 3 datasets, we achieve..." |
| 5 | Meta-analysis/review | "A review of 50 papers shows..." |

### Rigor (1-5)
| Score | Description | Example |
|-------|-------------|---------|
| 1 | No methodology | Results without methods |
| 2 | Incomplete methods | Missing key details |
| 3 | Standard methods | Basic experimental setup |
| 4 | Rigorous methods | Statistical tests, controls |
| 5 | Gold standard | Reproducibility, open data |

### Relevance (1-5)
| Score | Description | Example |
|-------|-------------|---------|
| 1 | Tangential | Different domain entirely |
| 2 | Loosely related | Same field, different problem |
| 3 | Related | Same problem class |
| 4 | Highly relevant | Direct comparison possible |
| 5 | Exact match | Same task, same metrics |

### Directness (1-5)
| Score | Description | Example |
|-------|-------------|---------|
| 1 | Heavy inference | Many assumptions needed |
| 2 | Moderate inference | Some extrapolation |
| 3 | Reasonable inference | Minor assumptions |
| 4 | Mostly direct | Clear implications |
| 5 | Direct support | Explicit statement |

### Reproducibility (1-5)
| Score | Description | Example |
|-------|-------------|---------|
| 1 | Not reproducible | Missing critical details |
| 2 | Partially described | Some details missing |
| 3 | Described | Could attempt reproduction |
| 4 | Detailed | High confidence reproduction |
| 5 | Fully reproducible | Code/data available |

## Verdict Assignment

### Approved (composite ≥3.0)
- Strong evidence from rigorous methodology
- Claims directly supported by data
- Reproducible results

### Rejected (composite <2.5)
- Weak or anecdotal evidence
- Missing methodology
- Overreaching claims

### Borderline (2.5 ≤ composite < 3.0)
- Mixed evidence quality
- Some methodological concerns
- Reasonable but not definitive

## Inter-Annotator Agreement

Target: ≥80% agreement on verdict (approved/rejected/borderline)

Resolution process:
1. Independent annotation by 2 reviewers
2. Compare verdicts
3. Discuss disagreements
4. Record final consensus
```

### 3. Per-Paper Annotation Files

**Directory:** `tests/golden_dataset/annotations/`

Each paper gets its own annotation file:
- `NEURO-001.json`
- `QUANTUM-001.json`
- `MICROBIO-001.json`
- etc.

### 4. Merged Golden Dataset Enhancement

**File:** `tests/golden_dataset/data/real_paper_claims.json`

```json
{
  "version": "1.0.0",
  "source": "real_paper_annotations",
  "generated": "2026-01-15T10:00:00Z",
  "statistics": {
    "total_claims": 480,
    "approved": 240,
    "rejected": 144,
    "borderline": 96,
    "domains": {
      "neuromorphic": 60,
      "quantum": 60,
      "microbio": 60,
      "fusion": 60,
      "nano_thermal": 60,
      "climate": 60,
      "materials": 60,
      "bioimaging": 60
    }
  },
  "claims": [...],
  "gaps": [...],
  "recommendations": [...]
}
```

---

## Annotation Targets by Category

| Category | Target | Purpose |
|----------|--------|---------|
| **Approved claims** | 200+ (50%) | True positive validation |
| **Rejected claims** | 120+ (30%) | True negative validation |
| **Borderline claims** | 80+ (20%) | Calibration testing |
| **Strong evidence** | 100+ | Strength score ≥4 |
| **Weak evidence** | 100+ | Strength score ≤2 |
| **High confidence** | 150+ | Verdict confidence = high |
| **Low confidence** | 50+ | Uncertainty handling |
| **Edge cases** | 40+ | Boundary condition testing |

---

## Domain Distribution

Each domain should have approximately equal representation:

| Domain | Papers | Claims | Gaps | Recommendations |
|--------|--------|--------|------|-----------------|
| Neuromorphic | 10 | 50-80 | 20+ | 10+ |
| Quantum | 10 | 50-80 | 20+ | 10+ |
| Microbiology | 10 | 50-80 | 20+ | 10+ |
| Fusion | 10 | 50-80 | 20+ | 10+ |
| Nanoparticle Heat | 10 | 50-80 | 20+ | 10+ |
| Climate | 10 | 50-80 | 20+ | 10+ |
| Materials | 10 | 50-80 | 20+ | 10+ |
| Biomedical Imaging | 10 | 50-80 | 20+ | 10+ |
| **Total** | **80** | **400-640** | **160+** | **80+** |

---

## Implementation Plan

### Phase 1: Setup (2 hours)
1. Create `annotate_paper.py` script
2. Create ANNOTATION_GUIDELINES.md
3. Set up annotations directory structure

### Phase 2: Pilot Annotation (4 hours)
1. Annotate 5 papers (1 from each high-priority domain)
2. Validate schema compatibility
3. Refine guidelines based on experience
4. Calculate initial inter-annotator agreement

### Phase 3: Full Annotation (12 hours)
1. Annotate remaining 75 papers
2. Target 6 claims per paper average
3. Ensure category balance (approved/rejected/borderline)
4. Regular validation checkpoints

### Phase 4: Merge & Validate (2 hours)
1. Run `annotate_paper.py merge`
2. Validate merged dataset against schema
3. Generate annotation quality report
4. Update paper registry with annotation status

---

## Quality Assurance

### Validation Checks

```python
def validate_annotation_quality(annotations_dir: Path):
    """Validate annotation quality metrics."""
    issues = []
    
    for file in annotations_dir.glob("*.json"):
        with open(file) as f:
            data = json.load(f)
        
        claims = data.get("claims", [])
        
        # Check minimum claims per paper
        if len(claims) < 5:
            issues.append(f"{file.stem}: Only {len(claims)} claims (need 5+)")
        
        # Check verdict distribution
        verdicts = [c["expected_verdict"] for c in claims]
        if verdicts.count("borderline") < 1:
            issues.append(f"{file.stem}: No borderline claims")
        
        # Check evidence quality ranges
        for claim in claims:
            eq = claim.get("evidence_quality", {})
            for field in ["strength_score", "rigor_score", "relevance_score"]:
                score = eq.get(field, 0)
                if not 1 <= score <= 5:
                    issues.append(f"{file.stem}: Invalid {field}={score}")
    
    return issues
```

### Inter-Annotator Agreement (Optional)

If multiple annotators are used:

```python
def calculate_agreement(annotations_a: List, annotations_b: List) -> float:
    """Calculate Cohen's Kappa for verdict agreement."""
    from sklearn.metrics import cohen_kappa_score
    
    verdicts_a = [a["expected_verdict"] for a in annotations_a]
    verdicts_b = [b["expected_verdict"] for b in annotations_b]
    
    return cohen_kappa_score(verdicts_a, verdicts_b)
```

---

## Acceptance Criteria

| Criterion | Target | Metric |
|-----------|--------|--------|
| Total Claims | 400+ | Merged dataset count |
| Per-Paper Average | 5-8 | claims / papers |
| Approved Ratio | 45-55% | approved / total |
| Rejected Ratio | 25-35% | rejected / total |
| Borderline Ratio | 15-25% | borderline / total |
| Domain Balance | ≤10% variance | max - min per domain |
| Schema Valid | 100% | All annotations pass validation |
| Gaps per Paper | 2+ | Total gaps ≥160 |
| Recommendations | 80+ | Total recommendations |

---

## Integration with Golden Dataset

After annotation, merge real paper claims with synthetic claims:

```python
def merge_golden_datasets():
    """Merge synthetic and real paper annotations."""
    
    # Load synthetic claims (VM-W1-4)
    with open("tests/golden_dataset/data/golden_dataset.json") as f:
        synthetic = json.load(f)
    
    # Load real paper annotations (this task)
    with open("tests/golden_dataset/data/real_paper_claims.json") as f:
        real = json.load(f)
    
    # Merge
    merged = {
        "version": "2.0.0",
        "claims": synthetic["claims"] + real["claims"],
        "gaps": synthetic["gaps"] + real["gaps"],
        "recommendations": synthetic["recommendations"] + real["recommendations"]
    }
    
    # Tag source
    for claim in merged["claims"]:
        if claim["claim_id"].startswith("GD-"):
            claim["source_type"] = "synthetic"
        else:
            claim["source_type"] = "real_paper"
    
    with open("tests/golden_dataset/data/golden_dataset_v2.json", "w") as f:
        json.dump(merged, f, indent=2)
```

---

## Notes

- **Quality over quantity** - Better to have fewer well-annotated claims than many poor ones
- **Consistency** - Follow guidelines strictly; inconsistency degrades benchmark quality
- **Documentation** - Record annotation decisions and edge cases
- **Iteration** - First batch may require guideline refinement
- **Domain expertise** - May need domain experts for specialized papers
