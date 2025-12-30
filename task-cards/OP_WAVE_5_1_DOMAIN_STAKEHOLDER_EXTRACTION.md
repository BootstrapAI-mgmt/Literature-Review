# Task Card: Domain Stakeholder Impact Extraction

**Task ID:** OP-W5-1  
**Wave:** 5 (Literature Extraction Enhancements)  
**Priority:** HIGH  
**Estimated Effort:** 12 hours  
**Status:** Not Started  
**Dependencies:** OP-W2-1 (Action/Gap Extraction), OP-W1-1 (Schema Foundation)  
**Blocks:** None (enables stakeholder-aware research prioritization)

---

## Objective

Extract **domain stakeholder impacts** as explicitly stated in research papers. This captures the relationship between research gaps identified in the literature and the field-specific stakeholders (e.g., "neuroscientists", "clinical researchers", "hardware engineers") who are affected by those gaps according to the papers themselves.

**This is DISTINCT from:**
- **Organizational Stakeholder Prioritization** (OP-W4-3/PR #104): Algorithmic mapping of gaps to internal team roles
- **Gap Analysis**: Our computed gaps vs. literature-stated gaps

## Background

Research papers often state relationships like:
> "The lack of validated energy-efficiency benchmarks **(gap)** limits the ability of **hardware engineers** **(stakeholder)** to optimize neuromorphic chip designs **(impact)**"

Currently, we extract gaps from papers but lose the stakeholder context. This task adds:

1. **Domain Stakeholder Extraction**: Capture stakeholder types as mentioned in papers (not predefined organizational roles)
2. **Gap-Stakeholder Linkage**: Link extracted stakeholders to specific gaps mentioned in the same paper
3. **Impact Statement Capture**: Record the exact impact statement connecting gap to stakeholder
4. **Resolution Tracking**: When a gap is filled by subsequent research, mark the stakeholder impact as resolved

## Success Criteria

- [ ] `domain_stakeholder_extractor.py` module created
- [ ] `LiteratureStakeholderImpact` dataclass implemented
- [ ] Extraction prompt added to deep reviewer pipeline
- [ ] Gap-stakeholder linkage algorithm working
- [ ] Impact statements captured with source quotes
- [ ] Resolution tracking when gaps are filled
- [ ] Integration with existing gap analysis
- [ ] `literature_stakeholder_impacts.json` output generated
- [ ] Unit tests with >90% coverage

---

## Deliverables

### 1. Data Structures (`literature_review/models/domain_stakeholder.py`)

```python
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class StakeholderCategory(Enum):
    """Broad categories for domain stakeholders."""
    RESEARCHER = "researcher"           # Academic researchers
    ENGINEER = "engineer"               # Hardware/software engineers  
    CLINICIAN = "clinician"             # Medical/clinical professionals
    PRACTITIONER = "practitioner"       # Industry practitioners
    POLICY_MAKER = "policy_maker"       # Policy/regulatory bodies
    END_USER = "end_user"               # End users of systems
    OTHER = "other"

@dataclass
class DomainStakeholder:
    """A stakeholder type as mentioned in research literature."""
    stakeholder_type: str           # e.g., "neuroscientists", "hardware engineers"
    category: StakeholderCategory   # Broad category
    description: str                # Context from paper
    source_papers: List[str] = field(default_factory=list)  # Papers mentioning this stakeholder
    
@dataclass
class LiteratureStakeholderImpact:
    """
    A stakeholder impact as stated in research literature.
    
    Captures the explicit statement from a paper that a specific gap
    affects a specific stakeholder type.
    """
    impact_id: str                      # Unique identifier
    
    # Gap information
    gap_id: str                         # Links to gap analysis
    gap_description: str                # Gap as stated in paper
    
    # Stakeholder information  
    affected_stakeholder: str           # Stakeholder type as stated (e.g., "neuroscientists")
    stakeholder_category: StakeholderCategory
    
    # Impact details
    impact_statement: str               # How the gap affects the stakeholder
    source_quote: Optional[str] = None  # Direct quote if available
    
    # Provenance
    source_paper: str                   # Paper filename
    paper_section: Optional[str] = None # Where in paper (e.g., "Discussion")
    extraction_confidence: float = 0.8  # 0-1 confidence score
    
    # Resolution tracking
    gap_filled: bool = False            # Updated when gap is closed
    filled_by_paper: Optional[str] = None  # Paper that filled the gap
    filled_date: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "impact_id": self.impact_id,
            "gap_id": self.gap_id,
            "gap_description": self.gap_description,
            "affected_stakeholder": self.affected_stakeholder,
            "stakeholder_category": self.stakeholder_category.value,
            "impact_statement": self.impact_statement,
            "source_quote": self.source_quote,
            "source_paper": self.source_paper,
            "paper_section": self.paper_section,
            "extraction_confidence": self.extraction_confidence,
            "gap_filled": self.gap_filled,
            "filled_by_paper": self.filled_by_paper,
            "filled_date": self.filled_date
        }
```

### 2. Extraction Prompt (Addition to Deep Reviewer)

Add to `literature_review/reviewers/prompts/stakeholder_extraction_prompt.py`:

```python
STAKEHOLDER_IMPACT_EXTRACTION_PROMPT = """
Analyze this research paper for **explicit statements** linking research gaps to affected stakeholders.

Look for statements where the paper:
1. Identifies a gap, limitation, or missing research
2. AND explicitly states who is affected by this gap (e.g., "researchers", "engineers", "clinicians")
3. AND describes HOW they are affected

For each gap-stakeholder-impact relationship found, extract:

1. **Gap Description**: The research gap as stated
2. **Affected Stakeholder**: The stakeholder type mentioned (use exact wording from paper)
3. **Stakeholder Category**: Classify as one of: researcher, engineer, clinician, practitioner, policy_maker, end_user, other
4. **Impact Statement**: How the gap affects the stakeholder
5. **Source Quote**: Direct quote from paper (if available)
6. **Paper Section**: Where found (Introduction, Methods, Discussion, Conclusion, etc.)
7. **Confidence**: How explicitly stated (0.5-1.0)

Return as JSON array. Only include impacts that are EXPLICITLY stated, not inferred.

Example output:
```json
[
  {
    "gap_description": "Lack of standardized benchmarks for neuromorphic energy efficiency",
    "affected_stakeholder": "hardware engineers",
    "stakeholder_category": "engineer", 
    "impact_statement": "Cannot objectively compare designs across platforms",
    "source_quote": "Without standardized benchmarks, hardware engineers cannot objectively compare neuromorphic designs...",
    "paper_section": "Discussion",
    "confidence": 0.95
  }
]
```

If no explicit gap-stakeholder impacts are found, return empty array: []
"""
```

### 3. Extractor Module (`literature_review/analysis/domain_stakeholder_extractor.py`)

```python
class DomainStakeholderExtractor:
    """
    Extract domain stakeholder impacts from research literature.
    
    Captures explicit statements linking research gaps to affected
    stakeholders as stated in papers.
    """
    
    def __init__(self, gap_analysis_path: str):
        """Initialize with gap analysis for linkage."""
        self.gap_analysis = self._load_gap_analysis(gap_analysis_path)
        self.impacts: List[LiteratureStakeholderImpact] = []
        self.stakeholders: Dict[str, DomainStakeholder] = {}
    
    def extract_from_paper(self, paper_content: str, filename: str) -> List[LiteratureStakeholderImpact]:
        """Extract stakeholder impacts from a single paper."""
        # Call LLM with extraction prompt
        # Parse response
        # Link to existing gaps where possible
        # Return list of impacts
        pass
    
    def link_to_gap_analysis(self, impact: LiteratureStakeholderImpact) -> Optional[str]:
        """Attempt to link extracted impact to existing gap analysis."""
        # Semantic matching to find corresponding gap
        pass
    
    def check_gap_resolution(self, new_paper: str) -> List[str]:
        """Check if new paper resolves any tracked gaps."""
        # Compare new paper claims against open gaps
        # Mark resolved and return list of resolved impact_ids
        pass
    
    def generate_report(self) -> Dict:
        """Generate stakeholder impact report."""
        return {
            "summary": {
                "total_impacts": len(self.impacts),
                "unique_stakeholders": len(self.stakeholders),
                "open_impacts": len([i for i in self.impacts if not i.gap_filled]),
                "resolved_impacts": len([i for i in self.impacts if i.gap_filled])
            },
            "stakeholders": {k: v.to_dict() for k, v in self.stakeholders.items()},
            "impacts_by_stakeholder": self._group_by_stakeholder(),
            "open_gaps_by_stakeholder": self._get_open_gaps_by_stakeholder(),
            "all_impacts": [i.to_dict() for i in self.impacts]
        }
    
    def save_report(self, output_path: str):
        """Save literature stakeholder impacts to file."""
        pass
```

### 4. Output Schema (`literature_stakeholder_impacts.json`)

```json
{
  "report_type": "literature_domain_stakeholder_impacts",
  "description": "Stakeholder impacts as explicitly stated in research literature",
  "generated_at": "2025-12-30T12:00:00Z",
  "summary": {
    "total_impacts": 45,
    "unique_stakeholders": 12,
    "open_impacts": 38,
    "resolved_impacts": 7,
    "papers_analyzed": 150
  },
  "stakeholders": {
    "neuroscientists": {
      "stakeholder_type": "neuroscientists",
      "category": "researcher",
      "description": "Researchers studying biological neural systems",
      "impact_count": 15,
      "source_papers": ["paper1.pdf", "paper2.pdf"]
    }
  },
  "impacts_by_stakeholder": {
    "neuroscientists": [
      {
        "impact_id": "LSI-001",
        "gap_description": "Missing spike timing validation data",
        "impact_statement": "Cannot validate computational models against biological recordings",
        "source_paper": "snn_review_2024.pdf",
        "gap_filled": false
      }
    ]
  },
  "open_gaps_by_stakeholder": {
    "neuroscientists": 12,
    "hardware_engineers": 8,
    "clinical_researchers": 5
  },
  "all_impacts": [...]
}
```

---

## Integration Points

### With Deep Reviewer Pipeline
- Add stakeholder extraction as optional pass after claim extraction
- Store results alongside other extracted data

### With Gap Analysis
- Link extracted stakeholder impacts to computed gaps
- Use gap resolution to update stakeholder impact status

### With Organizational Stakeholder Prioritization (OP-W4-3)
- Domain stakeholders (from literature) inform organizational stakeholder priorities
- e.g., if many papers cite "hardware engineers" as affected, increase priority weight for Engineering team

---

## Acceptance Criteria Checklist

- [ ] `DomainStakeholder` and `LiteratureStakeholderImpact` dataclasses complete
- [ ] Extraction prompt captures gap-stakeholder-impact triples
- [ ] Extractor correctly parses LLM responses
- [ ] Gap linkage uses semantic similarity
- [ ] Resolution tracking updates when gaps are filled
- [ ] Report generation includes all required summaries
- [ ] Integration with deep reviewer pipeline
- [ ] Unit tests pass with >90% coverage
- [ ] Manual validation on 5+ sample papers

---

## Comparison: Domain vs Organizational Stakeholders

| Aspect | Domain Stakeholders (This Task) | Organizational Stakeholders (OP-W4-3) |
|--------|--------------------------------|--------------------------------------|
| **Source** | Extracted from paper text | Predefined internal roles |
| **Examples** | "neuroscientists", "clinical researchers" | "Core Research Team", "Engineering Team" |
| **Purpose** | Track who literature says is affected | Internal resource allocation |
| **Gap Scope** | Only gaps where papers mention stakeholders | All identified gaps |
| **Resolution** | Marked when gap is filled by new research | N/A (algorithmic) |
| **Output** | `literature_stakeholder_impacts.json` | `organizational_stakeholder_prioritization_matrix.json` |

---

## Notes for Agent

1. **Extraction Quality**: Only extract EXPLICIT statements. Do not infer stakeholder impacts.

2. **Stakeholder Normalization**: Group similar stakeholder types:
   - "neuroscientists" and "neuroscience researchers" → same stakeholder
   - "hardware engineers" and "chip designers" → may be same or different based on context

3. **Gap Linkage**: Use embedding similarity to link extracted gaps to gap analysis:
   ```python
   similarity = cosine_similarity(
       embed(extracted_gap_description),
       embed(gap_analysis_gap_description)
   )
   if similarity > 0.8:
       link_gap(...)
   ```

4. **Resolution Detection**: When processing new papers, check if claims address open gaps:
   ```python
   for claim in new_paper_claims:
       for open_impact in get_open_impacts():
           if claim_addresses_gap(claim, open_impact.gap_description):
               mark_resolved(open_impact, new_paper)
   ```

5. **Confidence Thresholds**:
   - 0.9-1.0: Direct quote with explicit stakeholder mention
   - 0.7-0.9: Clear statement but paraphrased
   - 0.5-0.7: Implicit but reasonable inference
   - <0.5: Do not include
