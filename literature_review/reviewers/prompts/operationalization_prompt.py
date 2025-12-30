"""
Operationalization Extraction Prompts

These prompts extract implementation-focused metadata from papers
to support action vector generation.
"""

from typing import Dict, List


OPERATIONALIZATION_EXTRACTION_PROMPT = """
You are analyzing a research paper to extract operationalization information.
Your goal is to identify HOW the paper's findings can be implemented in practice.

For the following claim and evidence:

**Claim:** {claim_text}
**Evidence:** {evidence_chunk}
**Requirement:** {requirement_text}

Extract the following operationalization metadata:

## 1. Implementation Approach
What specific techniques, algorithms, or methods does the paper describe that could be replicated?
- Name the specific approach (e.g., "surrogate gradient training with SuperSpike")
- Identify key hyperparameters mentioned
- Note any implementation variants or alternatives mentioned

## 2. Reproducibility Assessment
Evaluate how reproducible this work is:

- **Code Available?** (yes/no) - Is source code provided or referenced?
  - If yes, provide URL
- **Data Available?** (yes/no) - Is training/test data available?
  - If yes, provide URL or dataset name
- **Hyperparameters Specified?** (yes/no) - Are key parameters documented?
- **Methodology Detail Level:** (high/medium/low)
  - high: Step-by-step instructions, all parameters, clear workflow
  - medium: Main steps clear, some details missing
  - low: High-level description only

## 3. Resource Requirements
What resources are needed to implement this?

- **Hardware:** (list specific requirements - GPU type, neuromorphic chip, sensors, etc.)
- **Software:** (list frameworks, libraries, tools)
- **Data:** (list datasets, data collection requirements)
- **Compute Time:** (estimate if mentioned - "hours on V100", etc.)
- **Personnel Skills:** (list required expertise)

## 4. Action Chain Position
Where does this fit in the implementation sequence?

- **Prerequisites:** What must be done/known BEFORE this can be implemented?
  - Reference specific capabilities, prior work, or other requirements
- **Enables:** What does successful implementation of this ENABLE next?
  - Reference downstream capabilities or requirements
- **Gaps:** What's MISSING from the paper to fully implement this?
  - Missing details, undefined parameters, unstated assumptions
- **Blocking Unknowns:** What questions MUST be answered before proceeding?

Return your analysis as JSON:

```json
{{
  "implementation_approach": {{
    "technique_name": "string",
    "description": "string",
    "key_hyperparameters": ["string"],
    "alternatives_mentioned": ["string"]
  }},
  "reproducibility": {{
    "code_available": boolean,
    "code_url": "string or null",
    "data_available": boolean,
    "data_url": "string or null",
    "hyperparameters_specified": boolean,
    "methodology_detail_level": "high|medium|low"
  }},
  "resources": {{
    "hardware": ["string"],
    "software": ["string"],
    "data": ["string"],
    "compute_time": "string or null",
    "personnel_skills": ["string"]
  }},
  "action_chain": {{
    "prerequisites": ["string"],
    "enables": ["string"],
    "gaps": ["string"],
    "blocking_unknowns": ["string"]
  }},
  "actionability_score": 0.0-1.0,
  "actionability_rationale": "string"
}}
```

The actionability_score should reflect:
- 1.0: Fully actionable - clear steps, all resources identified, no blockers
- 0.7-0.9: Mostly actionable - minor gaps or missing details
- 0.4-0.6: Partially actionable - significant gaps but core approach clear
- 0.1-0.3: Weakly actionable - major unknowns, unclear approach
- 0.0: Not actionable - no implementation guidance

Be specific and concrete. If information is not present in the paper, say so explicitly.
"""


BATCH_OPERATIONALIZATION_PROMPT = """
You are analyzing multiple claims from a single paper for operationalization.

**Paper:** {filename}

For each of the following claims, extract operationalization metadata.

{claims_section}

Return a JSON array with one object per claim:

```json
[
  {{
    "claim_id": "string",
    "operationalization": {{
      "implementation_approach": {{...}},
      "reproducibility": {{...}},
      "resources": {{...}},
      "action_chain": {{...}},
      "actionability_score": 0.0-1.0,
      "actionability_rationale": "string"
    }}
  }}
]
```

Focus on:
1. Concrete implementation details from the paper
2. Honest assessment of reproducibility
3. Realistic resource requirements
4. Clear action chain positioning

Be specific. Use "unknown" or null when information is genuinely missing.
"""


def format_claim_for_prompt(claim: Dict, requirement_text: str) -> str:
    """Format a single claim for the operationalization prompt."""
    claim_text = claim.get("extracted_claim_text", claim.get("claim_summary", ""))
    evidence_chunk = claim.get("evidence_chunk", "")
    
    return OPERATIONALIZATION_EXTRACTION_PROMPT.format(
        claim_text=claim_text,
        evidence_chunk=evidence_chunk,
        requirement_text=requirement_text
    )


def format_claims_batch(claims: List[Dict], filename: str) -> str:
    """Format multiple claims for batch extraction."""
    claims_section = ""
    for i, claim in enumerate(claims, 1):
        claim_id = claim.get("claim_id", f"claim_{i}")
        claim_text = claim.get("extracted_claim_text", claim.get("claim_summary", ""))
        evidence = claim.get("evidence_chunk", "")[:500]  # Truncate for batching
        requirement = claim.get("requirement_id", claim.get("sub_requirement", "Unknown requirement"))
        
        claims_section += f"""
---
**Claim {i}** (ID: {claim_id})
- Requirement: {requirement}
- Claim: {claim_text}
- Evidence: {evidence}...
---
"""
    
    return BATCH_OPERATIONALIZATION_PROMPT.format(
        filename=filename,
        claims_section=claims_section
    )
