# TASK CARD #23: Conflict-of-Interest Analysis (OPTIONAL)

**Priority:** 🟢 LOW (Optional Enhancement)  
**Estimated Effort:** 6-8 hours  
**Risk Level:** LOW  
**Wave:** Wave 3-4 (Optional)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #17 (Provenance Tracking)  
**Blocks:** None

## Problem Statement

Systematic reviews should assess potential conflicts of interest (COI) in source papers, as funding sources may bias findings. Currently:
- No tracking of funding sources or acknowledgments
- No identification of industry-sponsored research
- No flagging of potential COI
- Missing transparency required for systematic reviews

COI analysis is **optional** but recommended for regulatory submissions and high-stakes decision-making.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Extract funding acknowledgments from papers
- [ ] Identify industry vs. government vs. academic funding
- [ ] Detect author affiliations (industry vs. academic)
- [ ] Flag potential COI in claims
- [ ] Generate COI summary report

**COI Detection Patterns:**
- [ ] Funding keywords: "funded by", "supported by", "grant from"
- [ ] Industry affiliations: Company names, corporate labs
- [ ] Disclosure statements: "authors declare", "competing interests"
- [ ] Government grants: NSF, NIH, DARPA, etc.

**Technical Requirements:**
- [ ] COI extraction >70% accuracy on test papers
- [ ] Pattern matching for common funding sources
- [ ] COI metadata stored in provenance
- [ ] Processing time increase <10%

## Implementation Guide

### 1. New Module: literature_review/analysis/coi_analysis.py (~120 lines)

```python
import re
from typing import Dict, List, Optional

# Funding source patterns
FUNDING_PATTERNS = {
    "industry": [
        r"funded by [A-Z][a-z]+ (Inc\.|Corp\.|Ltd\.|Company)",
        r"sponsored by [A-Z][a-z]+ (Inc\.|Corp\.|Ltd\.)",
        r"support from [A-Z][a-z]+ (Inc\.|Corp\.|Ltd\.)",
        r"(Intel|NVIDIA|IBM|Google|Microsoft|Apple|Samsung|Qualcomm) (grant|funding)"
    ],
    "government": [
        r"(NSF|NIH|DARPA|DOE|DOD|NASA|AFOSR|ONR|ARO) (grant|award|funding)",
        r"National Science Foundation",
        r"National Institutes of Health",
        r"Defense Advanced Research Projects Agency"
    ],
    "academic": [
        r"university (grant|funding)",
        r"institutional support",
        r"internal funding",
        r"department of"
    ]
}

DISCLOSURE_PATTERNS = [
    r"authors declare no (competing|conflict)",
    r"authors have no (financial|competing) interests",
    r"no conflicts of interest",
    r"authors report the following (conflicts|competing interests)"
]

def extract_coi_metadata(full_text: str, filename: str) -> Dict:
    """
    Extract conflict-of-interest metadata from paper.
    
    Args:
        full_text: Full text of paper
        filename: Paper filename
        
    Returns:
        {
            "funding_sources": ["NSF Grant 12345", "Intel Corp"],
            "funding_type": "mixed",  # industry|government|academic|mixed|none
            "has_disclosure_statement": True,
            "potential_coi": True,
            "coi_notes": "Industry-funded research...",
            "extracted_text": "Funding: This work was supported by..."
        }
    """
    
    # Extract acknowledgments section
    ack_section = _extract_acknowledgments(full_text)
    
    if not ack_section:
        return {
            "funding_sources": [],
            "funding_type": "unknown",
            "has_disclosure_statement": False,
            "potential_coi": False,
            "coi_notes": "No acknowledgments section found",
            "extracted_text": None
        }
    
    # Detect funding sources
    funding_sources = []
    funding_types = set()
    
    for funding_type, patterns in FUNDING_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, ack_section, re.IGNORECASE)
            if matches:
                funding_types.add(funding_type)
                # Extract the actual text
                for match in re.finditer(pattern, ack_section, re.IGNORECASE):
                    context = ack_section[max(0, match.start()-50):match.end()+50]
                    funding_sources.append(context.strip())
    
    # Detect disclosure statements
    has_disclosure = any(
        re.search(pattern, ack_section, re.IGNORECASE)
        for pattern in DISCLOSURE_PATTERNS
    )
    
    # Determine overall funding type
    if not funding_types:
        overall_type = "none"
    elif len(funding_types) > 1:
        overall_type = "mixed"
    else:
        overall_type = list(funding_types)[0]
    
    # Assess potential COI
    potential_coi = "industry" in funding_types
    
    # Generate notes
    if potential_coi:
        coi_notes = f"Industry funding detected: {', '.join([s[:50] for s in funding_sources[:3]])}. Review for potential bias."
    elif overall_type == "government":
        coi_notes = "Government-funded research. Low COI risk."
    elif overall_type == "academic":
        coi_notes = "Academic/institutional funding. Low COI risk."
    else:
        coi_notes = "No clear funding source identified."
    
    return {
        "funding_sources": funding_sources,
        "funding_type": overall_type,
        "has_disclosure_statement": has_disclosure,
        "potential_coi": potential_coi,
        "coi_notes": coi_notes,
        "extracted_text": ack_section[:500]  # Truncate
    }

def _extract_acknowledgments(full_text: str) -> Optional[str]:
    """
    Extract acknowledgments/funding section from paper.
    
    Looks for common section headings.
    """
    # Common acknowledgment headings
    headings = [
        r"acknowledgments?",
        r"funding",
        r"financial (support|disclosure)",
        r"competing interests",
        r"conflict of interest",
        r"author contributions"
    ]
    
    for heading in headings:
        # Look for heading pattern
        pattern = rf"\b{heading}\b.*?(?=\n\s*\n|\Z)"
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            # Extract text (up to 2000 chars or next section)
            section_text = match.group(0)
            return section_text[:2000]
    
    return None

def generate_coi_report(db: pd.DataFrame, output_file: str):
    """Generate COI summary report."""
    
    coi_summary = {
        "industry": 0,
        "government": 0,
        "academic": 0,
        "mixed": 0,
        "none": 0,
        "unknown": 0
    }
    
    potential_coi_papers = []
    
    for _, row in db.iterrows():
        coi_metadata = row.get("COI_METADATA", {})
        if isinstance(coi_metadata, dict):
            funding_type = coi_metadata.get("funding_type", "unknown")
            coi_summary[funding_type] = coi_summary.get(funding_type, 0) + 1
            
            if coi_metadata.get("potential_coi"):
                potential_coi_papers.append({
                    "filename": row.get("Filename"),
                    "funding": coi_metadata.get("funding_sources", []),
                    "notes": coi_metadata.get("coi_notes")
                })
    
    # Write report
    with open(output_file, 'w') as f:
        f.write("# Conflict-of-Interest Analysis Report\n\n")
        f.write("## Funding Source Distribution\n\n")
        
        total_papers = sum(coi_summary.values())
        for funding_type, count in sorted(coi_summary.items(), key=lambda x: -x[1]):
            pct = (count / total_papers * 100) if total_papers > 0 else 0
            f.write(f"- **{funding_type.title()}**: {count} papers ({pct:.1f}%)\n")
        
        f.write(f"\n**Total Papers Analyzed:** {total_papers}\n\n")
        
        if potential_coi_papers:
            f.write(f"## ⚠️ Potential Conflicts of Interest ({len(potential_coi_papers)} papers)\n\n")
            for paper in potential_coi_papers:
                f.write(f"### {paper['filename']}\n")
                f.write(f"**Funding:** {', '.join(paper['funding'][:3])}\n\n")
                f.write(f"**Notes:** {paper['notes']}\n\n")
                f.write("---\n\n")
```

### 2. Integration with literature_review/reviewers/journal_reviewer.py (~30 lines)

```python
def extract_with_coi_metadata(file_path: str) -> Dict:
    """Extract text and COI metadata."""
    
    # Standard extraction
    full_text = extract_text_from_pdf(file_path)
    
    # Add COI analysis
    from literature_review.analysis.coi_analysis import extract_coi_metadata
    coi_metadata = extract_coi_metadata(full_text, os.path.basename(file_path))
    
    return {
        "text": full_text,
        "coi_metadata": coi_metadata
    }
```

## Testing Strategy

### Unit Tests

```python
from literature_review.analysis.coi_analysis import (
    extract_coi_metadata,
    _extract_acknowledgments
)

@pytest.mark.unit
def test_funding_detection():
    """Test funding source detection."""
    text = "This work was funded by Intel Corporation grant 12345."
    
    coi = extract_coi_metadata(text, "test.pdf")
    
    assert coi["funding_type"] == "industry"
    assert coi["potential_coi"] == True
    assert "Intel" in coi["coi_notes"]

@pytest.mark.unit
def test_government_funding():
    """Test government funding detection."""
    text = "Supported by NSF grant IIS-123456 and NIH award R01-789."
    
    coi = extract_coi_metadata(text, "test.pdf")
    
    assert coi["funding_type"] == "government"
    assert coi["potential_coi"] == False

@pytest.mark.unit
def test_disclosure_statement():
    """Test disclosure statement detection."""
    text = "The authors declare no competing financial interests."
    
    coi = extract_coi_metadata(text, "test.pdf")
    
    assert coi["has_disclosure_statement"] == True
```

## Success Criteria

- [ ] COI extraction >70% accurate on test papers
- [ ] Funding type classification correct
- [ ] Industry vs. government vs. academic distinction clear
- [ ] Potential COI flagged correctly
- [ ] COI report generated successfully
- [ ] Processing time increase <10%
- [ ] Unit tests pass (85% coverage)

## Benefits

1. **Transparency** - Disclose funding sources
2. **Bias awareness** - Flag industry-sponsored research
3. **Systematic review quality** - Meet PRISMA reporting standards
4. **Regulatory compliance** - Required for FDA/EMA submissions

## Limitations

- Pattern matching may miss non-standard acknowledgments
- Accuracy depends on PDF text extraction quality
- Manual review recommended for high-stakes decisions

---

**Status:** Optional enhancement  
**Wave:** Wave 3-4 (if needed)  
**Next Steps:** Evaluate necessity for current review, implement literature_review/analysis/coi_analysis.py if required for publication or regulatory submission
