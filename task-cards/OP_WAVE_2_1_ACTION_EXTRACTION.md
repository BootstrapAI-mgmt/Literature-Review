# Task Card: Action Extraction from Deep Review

**Task ID:** OP-W2-1  
**Wave:** 2 (Extraction Enhancement)  
**Priority:** HIGH  
**Estimated Effort:** 12 hours  
**Status:** Not Started  
**Dependencies:** OP-W1-1 (Schema Foundation)  
**Blocks:** OP-W3-2 (Action Vector Generator)

---

## Objective

Extend the Deep Reviewer to extract operationalization metadata from papers, including implementation approaches, reproducibility information, resource requirements, and action chain positioning.

## Background

Currently, the Deep Reviewer (`deep_reviewer.py`) extracts:
- Claims and evidence chunks
- Sub-requirement mappings
- Evidence quality scores

This task adds extraction of:
- **Implementation approaches**: Specific techniques, algorithms, methods
- **Reproducibility metadata**: Code/data availability, methodology detail
- **Resource requirements**: Hardware, software, data needs
- **Action chain position**: Prerequisites, enables, gaps

## Success Criteria

- [ ] Operationalization prompt added to Deep Reviewer
- [ ] Extracted data conforms to ActionVector schema (OP-W1-1)
- [ ] Judge scores actionability of claims
- [ ] Extraction works for existing paper formats
- [ ] Unit tests cover new extraction logic
- [ ] Integration test validates full pipeline

---

## Deliverables

### 1. Operationalization Extraction Prompt

**File:** `literature_review/reviewers/prompts/operationalization_prompt.py`

```python
"""
Operationalization Extraction Prompts

These prompts extract implementation-focused metadata from papers
to support action vector generation.
"""

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


def format_claim_for_prompt(claim: dict, requirement_text: str) -> str:
    """Format a single claim for the operationalization prompt."""
    claim_text = claim.get("extracted_claim_text", claim.get("claim_summary", ""))
    evidence_chunk = claim.get("evidence_chunk", "")
    
    return OPERATIONALIZATION_EXTRACTION_PROMPT.format(
        claim_text=claim_text,
        evidence_chunk=evidence_chunk,
        requirement_text=requirement_text
    )


def format_claims_batch(claims: list, filename: str) -> str:
    """Format multiple claims for batch extraction."""
    claims_section = ""
    for i, claim in enumerate(claims, 1):
        claim_id = claim.get("claim_id", f"claim_{i}")
        claim_text = claim.get("extracted_claim_text", claim.get("claim_summary", ""))
        evidence = claim.get("evidence_chunk", "")[:500]  # Truncate for batching
        requirement = claim.get("requirement_id", "Unknown requirement")
        
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
```

### 2. Deep Reviewer Integration

**File:** `literature_review/reviewers/deep_reviewer.py` (modifications)

Add the following to the existing deep_reviewer.py:

```python
# Add to imports
from literature_review.reviewers.prompts.operationalization_prompt import (
    format_claim_for_prompt,
    format_claims_batch
)
from literature_review.models import (
    ReproducibilityInfo,
    ResourceRequirements,
    ActionChainPosition
)

# Add new method to DeepReviewer class
class DeepReviewer:
    # ... existing code ...
    
    def extract_operationalization(
        self,
        claims: List[Dict],
        filename: str,
        batch_mode: bool = True
    ) -> Dict[str, Dict]:
        """
        Extract operationalization metadata for approved claims.
        
        Args:
            claims: List of claim dictionaries with evidence
            filename: Source paper filename
            batch_mode: If True, process all claims in one API call
        
        Returns:
            Dictionary mapping claim_id to operationalization data
        """
        if not claims:
            return {}
        
        logger.info(f"Extracting operationalization for {len(claims)} claims from {filename}")
        
        if batch_mode and len(claims) > 1:
            return self._extract_operationalization_batch(claims, filename)
        else:
            return self._extract_operationalization_individual(claims)
    
    def _extract_operationalization_batch(
        self,
        claims: List[Dict],
        filename: str
    ) -> Dict[str, Dict]:
        """Extract operationalization in batch mode."""
        prompt = format_claims_batch(claims, filename)
        
        try:
            response = self.api_manager.cached_api_call(
                prompt,
                use_cache=True,
                is_json=True,
                cache_prefix="operationalization"
            )
            
            if not response or not isinstance(response, list):
                logger.warning(f"Invalid batch response for {filename}")
                return {}
            
            result = {}
            for item in response:
                claim_id = item.get("claim_id")
                if claim_id:
                    result[claim_id] = self._parse_operationalization(
                        item.get("operationalization", {})
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Batch operationalization extraction failed: {e}")
            # Fallback to individual
            return self._extract_operationalization_individual(claims)
    
    def _extract_operationalization_individual(
        self,
        claims: List[Dict]
    ) -> Dict[str, Dict]:
        """Extract operationalization for each claim individually."""
        result = {}
        
        for claim in claims:
            claim_id = claim.get("claim_id", "unknown")
            requirement_text = claim.get("requirement_text", "")
            
            prompt = format_claim_for_prompt(claim, requirement_text)
            
            try:
                response = self.api_manager.cached_api_call(
                    prompt,
                    use_cache=True,
                    is_json=True,
                    cache_prefix="operationalization"
                )
                
                if response:
                    result[claim_id] = self._parse_operationalization(response)
                    
            except Exception as e:
                logger.warning(f"Failed to extract operationalization for {claim_id}: {e}")
                continue
        
        return result
    
    def _parse_operationalization(self, data: Dict) -> Dict:
        """Parse and validate operationalization data."""
        # Create structured objects from response
        reproducibility = ReproducibilityInfo(
            code_available=data.get("reproducibility", {}).get("code_available", False),
            code_url=data.get("reproducibility", {}).get("code_url"),
            data_available=data.get("reproducibility", {}).get("data_available", False),
            data_url=data.get("reproducibility", {}).get("data_url"),
            hyperparameters_specified=data.get("reproducibility", {}).get("hyperparameters_specified", False),
            methodology_detail_level=data.get("reproducibility", {}).get("methodology_detail_level", "low")
        )
        
        resources = ResourceRequirements(
            hardware=data.get("resources", {}).get("hardware", []),
            software=data.get("resources", {}).get("software", []),
            data=data.get("resources", {}).get("data", []),
            compute_time=data.get("resources", {}).get("compute_time"),
            personnel_skills=data.get("resources", {}).get("personnel_skills", [])
        )
        
        action_chain = ActionChainPosition(
            prerequisites=data.get("action_chain", {}).get("prerequisites", []),
            enables=data.get("action_chain", {}).get("enables", []),
            gaps=data.get("action_chain", {}).get("gaps", []),
            blocking_unknowns=data.get("action_chain", {}).get("blocking_unknowns", [])
        )
        
        return {
            "implementation_approach": data.get("implementation_approach", {}),
            "reproducibility": reproducibility.to_dict(),
            "resources": resources.to_dict(),
            "action_chain": action_chain.to_dict(),
            "actionability_score": data.get("actionability_score", 0.0),
            "actionability_rationale": data.get("actionability_rationale", "")
        }
```

### 3. Judge Actionability Scoring

**File:** `literature_review/analysis/judge.py` (modifications)

Add actionability to evidence quality assessment:

```python
# Add to existing EvidenceQuality scoring

ACTIONABILITY_PROMPT = """
Evaluate the actionability of this evidence claim:

**Claim:** {claim_text}
**Evidence:** {evidence_chunk}

Actionability measures how directly this evidence can be translated into implementation steps.

Score from 1-5:
- 5: Highly actionable - Clear algorithm/method, parameters specified, directly implementable
- 4: Actionable - Method clear, some parameters need inference
- 3: Moderately actionable - Approach clear, significant details missing
- 2: Weakly actionable - High-level approach only, major gaps
- 1: Not actionable - Theoretical/conceptual, no implementation guidance

Also assess:
- implementation_clarity: How clear is the implementation path? (1-5)
- parameter_completeness: Are parameters/hyperparameters specified? (1-5)
- replication_feasibility: How feasible is replication? (1-5)

Return JSON:
{{
  "actionability_score": 1-5,
  "implementation_clarity": 1-5,
  "parameter_completeness": 1-5,
  "replication_feasibility": 1-5,
  "rationale": "string"
}}
"""


class Judge:
    # ... existing code ...
    
    def assess_actionability(self, claim: Dict) -> Dict:
        """
        Assess how actionable a claim is for implementation.
        
        Args:
            claim: Claim dictionary with evidence
        
        Returns:
            Actionability assessment dictionary
        """
        claim_text = claim.get("extracted_claim_text", claim.get("claim_summary", ""))
        evidence_chunk = claim.get("evidence_chunk", "")
        
        prompt = ACTIONABILITY_PROMPT.format(
            claim_text=claim_text,
            evidence_chunk=evidence_chunk
        )
        
        try:
            response = self.api_manager.cached_api_call(
                prompt,
                use_cache=True,
                is_json=True,
                cache_prefix="actionability"
            )
            
            if response:
                return {
                    "actionability_score": response.get("actionability_score", 3),
                    "implementation_clarity": response.get("implementation_clarity", 3),
                    "parameter_completeness": response.get("parameter_completeness", 3),
                    "replication_feasibility": response.get("replication_feasibility", 3),
                    "rationale": response.get("rationale", "")
                }
        except Exception as e:
            logger.warning(f"Actionability assessment failed: {e}")
        
        # Default to neutral scores
        return {
            "actionability_score": 3,
            "implementation_clarity": 3,
            "parameter_completeness": 3,
            "replication_feasibility": 3,
            "rationale": "Assessment failed"
        }
    
    def enhanced_judge_claim(self, claim: Dict, include_actionability: bool = True) -> Dict:
        """
        Enhanced claim judging that includes actionability assessment.
        
        Args:
            claim: Claim dictionary to judge
            include_actionability: Whether to include actionability scoring
        
        Returns:
            Enhanced judgment with evidence quality and actionability
        """
        # Existing judgment logic
        base_judgment = self.judge_claim(claim)
        
        if include_actionability and base_judgment.get("verdict") == "approved":
            actionability = self.assess_actionability(claim)
            base_judgment["actionability"] = actionability
            
            # Incorporate into composite score (optional weighting)
            if "evidence_quality" in base_judgment:
                eq = base_judgment["evidence_quality"]
                action_normalized = actionability["actionability_score"] / 5.0
                
                # Add actionability as additional dimension
                eq["actionability"] = actionability["actionability_score"]
                eq["actionability_weight"] = 0.1  # 10% weight
                
                # Recalculate composite with actionability
                # Original: strength*0.30 + rigor*0.25 + relevance*0.25 + directness*0.10 + recency*0.05 + reproducibility*0.05
                # New: reduce others slightly to add 0.10 for actionability
                original_composite = eq.get("composite_score", 3.0)
                eq["composite_score_with_actionability"] = (
                    original_composite * 0.9 + action_normalized * 5.0 * 0.1
                )
        
        return base_judgment
```

### 4. Pipeline Integration

**File:** `literature_review/orchestrator.py` (modifications)

Add operationalization extraction to the pipeline:

```python
# Add to orchestrator's deep review processing

def run_deep_review_with_operationalization(
    self,
    papers: List[str],
    extract_operationalization: bool = True
) -> Dict:
    """
    Run deep review with optional operationalization extraction.
    
    Args:
        papers: List of paper filenames to process
        extract_operationalization: Whether to extract operationalization data
    
    Returns:
        Deep review results with operationalization data
    """
    # Run standard deep review
    deep_results = self.deep_reviewer.process_papers(papers)
    
    if extract_operationalization:
        logger.info("Extracting operationalization metadata...")
        
        for filename, paper_results in deep_results.items():
            approved_claims = [
                claim for claim in paper_results.get("claims", [])
                if claim.get("status") == "approved"
            ]
            
            if approved_claims:
                operationalization = self.deep_reviewer.extract_operationalization(
                    claims=approved_claims,
                    filename=filename
                )
                
                # Attach operationalization to claims
                for claim in paper_results.get("claims", []):
                    claim_id = claim.get("claim_id")
                    if claim_id and claim_id in operationalization:
                        claim["operationalization"] = operationalization[claim_id]
        
        logger.info("✅ Operationalization extraction complete")
    
    return deep_results
```

---

## Unit Tests

**File:** `tests/unit/test_operationalization_extraction.py`

```python
"""Unit tests for operationalization extraction."""

import pytest
from unittest.mock import Mock, patch

from literature_review.reviewers.prompts.operationalization_prompt import (
    format_claim_for_prompt,
    format_claims_batch,
    OPERATIONALIZATION_EXTRACTION_PROMPT
)


class TestOperationalizationPrompts:
    """Tests for operationalization prompt formatting."""
    
    def test_format_single_claim(self):
        """Test formatting a single claim."""
        claim = {
            "extracted_claim_text": "SNNs achieve 95% accuracy",
            "evidence_chunk": "We trained an SNN using surrogate gradients...",
            "requirement_id": "Sub-2.1.1"
        }
        
        prompt = format_claim_for_prompt(claim, "Event-based sensor integration")
        
        assert "SNNs achieve 95% accuracy" in prompt
        assert "Event-based sensor integration" in prompt
        assert "Implementation Approach" in prompt
        assert "Reproducibility Assessment" in prompt
    
    def test_format_claims_batch(self):
        """Test formatting multiple claims for batch processing."""
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "Claim 1",
                "evidence_chunk": "Evidence 1",
                "requirement_id": "Req 1"
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Claim 2",
                "evidence_chunk": "Evidence 2",
                "requirement_id": "Req 2"
            }
        ]
        
        prompt = format_claims_batch(claims, "test_paper.pdf")
        
        assert "test_paper.pdf" in prompt
        assert "Claim 1" in prompt
        assert "Claim 2" in prompt
        assert "c1" in prompt
        assert "c2" in prompt


class TestDeepReviewerOperationalization:
    """Tests for DeepReviewer operationalization extraction."""
    
    @pytest.fixture
    def mock_api_manager(self):
        """Create mock API manager."""
        mock = Mock()
        mock.cached_api_call.return_value = {
            "implementation_approach": {
                "technique_name": "Surrogate gradient",
                "description": "Use SuperSpike function"
            },
            "reproducibility": {
                "code_available": True,
                "code_url": "https://github.com/example",
                "data_available": True,
                "methodology_detail_level": "high"
            },
            "resources": {
                "hardware": ["NVIDIA V100"],
                "software": ["PyTorch", "snnTorch"]
            },
            "action_chain": {
                "prerequisites": ["CUDA setup"],
                "enables": ["SNN training"],
                "gaps": ["Hyperparameter tuning details"],
                "blocking_unknowns": []
            },
            "actionability_score": 0.85,
            "actionability_rationale": "Clear implementation with code"
        }
        return mock
    
    def test_parse_operationalization(self, mock_api_manager):
        """Test parsing operationalization response."""
        from literature_review.reviewers.deep_reviewer import DeepReviewer
        
        # Create minimal DeepReviewer for testing
        with patch.object(DeepReviewer, '__init__', lambda x: None):
            reviewer = DeepReviewer()
            reviewer.api_manager = mock_api_manager
            
            result = reviewer._parse_operationalization({
                "reproducibility": {
                    "code_available": True,
                    "code_url": "https://github.com/test",
                    "data_available": False,
                    "methodology_detail_level": "medium"
                },
                "resources": {
                    "hardware": ["GPU"],
                    "software": ["PyTorch"]
                },
                "action_chain": {
                    "prerequisites": [],
                    "enables": ["next step"],
                    "gaps": ["missing detail"]
                },
                "actionability_score": 0.7
            })
            
            assert result["reproducibility"]["code_available"] is True
            assert "reproducibility_score" in result["reproducibility"]
            assert result["resources"]["hardware"] == ["GPU"]
            assert len(result["action_chain"]["gaps"]) == 1


class TestJudgeActionability:
    """Tests for Judge actionability scoring."""
    
    @pytest.fixture
    def mock_judge(self):
        """Create mock Judge instance."""
        from literature_review.analysis.judge import Judge
        
        with patch.object(Judge, '__init__', lambda x: None):
            judge = Judge()
            judge.api_manager = Mock()
            judge.api_manager.cached_api_call.return_value = {
                "actionability_score": 4,
                "implementation_clarity": 4,
                "parameter_completeness": 3,
                "replication_feasibility": 4,
                "rationale": "Clear implementation approach"
            }
            return judge
    
    def test_assess_actionability(self, mock_judge):
        """Test actionability assessment."""
        claim = {
            "extracted_claim_text": "Our method achieves 95% accuracy",
            "evidence_chunk": "We use a 3-layer SNN with LIF neurons..."
        }
        
        result = mock_judge.assess_actionability(claim)
        
        assert result["actionability_score"] == 4
        assert result["implementation_clarity"] == 4
        assert "rationale" in result
```

---

## Integration Tests

**File:** `tests/integration/test_operationalization_pipeline.py`

```python
"""Integration tests for operationalization extraction pipeline."""

import pytest
import json
from pathlib import Path


@pytest.mark.integration
class TestOperationalizationPipeline:
    """Integration tests for full operationalization extraction."""
    
    def test_end_to_end_extraction(self, sample_paper, temp_output_dir):
        """Test full extraction pipeline."""
        from literature_review.orchestrator import Orchestrator
        
        # Run orchestrator with operationalization
        orchestrator = Orchestrator(output_dir=temp_output_dir)
        results = orchestrator.run_deep_review_with_operationalization(
            papers=[sample_paper],
            extract_operationalization=True
        )
        
        # Verify operationalization data attached
        assert sample_paper in results
        paper_results = results[sample_paper]
        
        approved_claims = [
            c for c in paper_results.get("claims", [])
            if c.get("status") == "approved"
        ]
        
        # At least some claims should have operationalization
        claims_with_ops = [
            c for c in approved_claims
            if "operationalization" in c
        ]
        
        assert len(claims_with_ops) > 0, "No operationalization data extracted"
        
        # Verify structure
        for claim in claims_with_ops:
            ops = claim["operationalization"]
            assert "reproducibility" in ops
            assert "resources" in ops
            assert "action_chain" in ops
            assert "actionability_score" in ops
    
    def test_operationalization_saved_to_output(self, temp_output_dir):
        """Test that operationalization is saved to output files."""
        # Run pipeline and check output files contain operationalization
        pass  # Implementation depends on output format
```

---

## Acceptance Criteria Checklist

- [ ] Operationalization prompt extracts all required fields
- [ ] Batch mode processes multiple claims efficiently
- [ ] Individual mode fallback works when batch fails
- [ ] ReproducibilityInfo, ResourceRequirements, ActionChainPosition properly created
- [ ] Judge actionability scoring integrated
- [ ] Composite score optionally includes actionability
- [ ] Pipeline orchestrator calls operationalization extraction
- [ ] Operationalization data attached to claim objects
- [ ] Unit tests pass with >90% coverage
- [ ] Integration test validates end-to-end flow
- [ ] API costs remain reasonable (batch mode reduces calls)

---

## Performance Considerations

1. **API Call Efficiency:**
   - Batch mode processes up to 10 claims per API call
   - ~70% reduction in API calls vs individual mode
   - Cache prefix prevents duplicate extraction

2. **Processing Time:**
   - Expect ~2-3 seconds per claim in individual mode
   - ~10-15 seconds per batch of 10 claims
   - Total overhead: ~20% increase in deep review time

3. **Memory:**
   - Operationalization data adds ~2KB per claim
   - No significant memory impact for typical runs

---

## Rollback Plan

If issues arise:

1. **Disable Operationalization:**
   ```python
   # In orchestrator config
   orchestrator.run_deep_review_with_operationalization(
       papers=papers,
       extract_operationalization=False  # Disable
   )
   ```

2. **Remove Integration:**
   - Revert modifications to deep_reviewer.py
   - Revert modifications to judge.py
   - New prompt file can remain (unused)

3. **Git Revert:**
   - Single commit for easy revert

---

## Notes for Agent

1. **Create prompts directory first:**
   ```bash
   mkdir -p literature_review/reviewers/prompts
   touch literature_review/reviewers/prompts/__init__.py
   ```

2. **Test prompts with sample data before integration:**
   ```python
   from literature_review.reviewers.prompts.operationalization_prompt import format_claim_for_prompt
   
   sample_claim = {"extracted_claim_text": "test", "evidence_chunk": "test"}
   print(format_claim_for_prompt(sample_claim, "test requirement"))
   ```

3. **Verify API response parsing:**
   - LLM may return slightly different JSON structures
   - Add defensive parsing with defaults

4. **Monitor API costs during testing:**
   - Each claim adds 1 API call (or 1/10 in batch mode)
   - Use cache aggressively during development
