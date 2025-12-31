"""
Stakeholder Impact Extraction Prompts

These prompts extract domain stakeholder impacts from research papers,
capturing explicit statements linking research gaps to affected stakeholders.
"""

from typing import Dict, List


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

--- PAPER CONTENT ---
{paper_content}
--- END PAPER CONTENT ---

Example output:
```json
[
  {{
    "gap_description": "Lack of standardized benchmarks for neuromorphic energy efficiency",
    "affected_stakeholder": "hardware engineers",
    "stakeholder_category": "engineer",
    "impact_statement": "Cannot objectively compare designs across platforms",
    "source_quote": "Without standardized benchmarks, hardware engineers cannot objectively compare neuromorphic designs...",
    "paper_section": "Discussion",
    "confidence": 0.95
  }}
]
```

If no explicit gap-stakeholder impacts are found, return empty array: []
"""


STAKEHOLDER_IMPACT_BATCH_PROMPT = """
Analyze the following research paper excerpts for **explicit statements** linking research gaps to affected stakeholders.

**Paper:** {filename}

Look for statements where the paper:
1. Identifies a gap, limitation, or missing research
2. AND explicitly states who is affected by this gap
3. AND describes HOW they are affected

{paper_sections}

For each gap-stakeholder-impact relationship found, extract:
- gap_description: The research gap as stated
- affected_stakeholder: The stakeholder type mentioned (use exact wording)
- stakeholder_category: One of: researcher, engineer, clinician, practitioner, policy_maker, end_user, other
- impact_statement: How the gap affects the stakeholder
- source_quote: Direct quote from paper (if available)
- paper_section: Where found
- confidence: How explicitly stated (0.5-1.0)

Return as JSON array. Only include impacts that are EXPLICITLY stated, not inferred.
If no explicit impacts are found, return empty array: []
"""


# Configuration constants
MIN_CONFIDENCE_THRESHOLD = 0.5
MAX_IMPACTS_PER_PAPER = 10


def format_stakeholder_extraction_prompt(paper_content: str) -> str:
    """
    Format the stakeholder extraction prompt with paper content.
    
    Args:
        paper_content: The full text content of the paper
        
    Returns:
        Formatted prompt string
    """
    return STAKEHOLDER_IMPACT_EXTRACTION_PROMPT.format(
        paper_content=paper_content
    )


def format_stakeholder_batch_prompt(
    filename: str,
    paper_sections: List[Dict[str, str]]
) -> str:
    """
    Format a batch prompt for stakeholder extraction from paper sections.
    
    Args:
        filename: Paper filename
        paper_sections: List of dicts with 'section_name' and 'content' keys
        
    Returns:
        Formatted batch prompt string
    """
    sections_text = ""
    for section in paper_sections:
        section_name = section.get("section_name", "Unknown")
        content = section.get("content", "")
        sections_text += f"\n--- {section_name} ---\n{content}\n"
    
    return STAKEHOLDER_IMPACT_BATCH_PROMPT.format(
        filename=filename,
        paper_sections=sections_text
    )


def parse_extraction_response(response: List[Dict]) -> List[Dict]:
    """
    Parse and validate the extraction response.
    
    Args:
        response: Raw response from LLM
        
    Returns:
        Validated list of extracted impacts
    """
    validated = []
    
    for item in response:
        # Check required fields
        if not all(key in item for key in [
            "gap_description", 
            "affected_stakeholder", 
            "impact_statement"
        ]):
            continue
        
        # Validate confidence threshold
        confidence = item.get("confidence", 0.5)
        if confidence < MIN_CONFIDENCE_THRESHOLD:
            continue
        
        # Normalize stakeholder category
        category = item.get("stakeholder_category", "other").lower()
        valid_categories = [
            "researcher", "engineer", "clinician", 
            "practitioner", "policy_maker", "end_user", "other"
        ]
        if category not in valid_categories:
            category = "other"
        
        validated.append({
            "gap_description": item["gap_description"],
            "affected_stakeholder": item["affected_stakeholder"],
            "stakeholder_category": category,
            "impact_statement": item["impact_statement"],
            "source_quote": item.get("source_quote"),
            "paper_section": item.get("paper_section"),
            "confidence": confidence
        })
    
    # Limit to max impacts per paper
    return validated[:MAX_IMPACTS_PER_PAPER]
