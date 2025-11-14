# Evidence Enhancement Test Modifications Guide

**Date Created:** November 13, 2025  
**Purpose:** Detailed guide for updating integration tests to validate evidence quality enhancements  
**Scope:** Modifications to existing Task Cards #6-12 (integration and E2E tests)

---

## 📋 Overview

Evidence enhancement task cards (#16-23) introduce new quality features that must be validated through the existing integration test suite. This document specifies exactly how to modify each integration test task card to include evidence quality validation.

**Test Cards to Modify:**
- **Wave 2 Tests**: Task Cards #6 (INT-001), #7 (INT-003)
- **Wave 3 Tests**: Task Cards #8 (INT-002), #9 (INT-004/005)
- **Wave 4 Tests**: Task Cards #10 (E2E-001), #11 (E2E-002)

---

## 🎯 Wave 2 Test Modifications

### Task Card #6: INT-001 (Journal-Reviewer → Judge Flow)

**Original Scope:** Test that Journal-Reviewer extracts claims and Judge evaluates them

**Enhanced Scope:** Add validation of multi-dimensional scoring (#16) and provenance tracking (#17)

#### New Test Cases to Add

**1. Test Multi-Dimensional Evidence Scoring**

```python
from literature_review.analysis.judge import Judge
from literature_review.reviewers.journal_reviewer import JournalReviewer
from unittest.mock import patch
import json

@pytest.mark.integration
def test_judge_outputs_multidimensional_scores(temp_workspace, test_data_generator):
    """
    Test that Judge outputs 6-dimensional evidence quality scores.
    
    Validates:
    - All 6 dimensions present (strength, rigor, relevance, directness, recency, reproducibility)
    - Composite score calculated correctly
    - Scores within valid ranges
    - Evidence quality metadata persisted in version history
    """
    # Setup: Create test paper with known quality
    test_pdf = test_data_generator.create_test_pdf(
        content="Strong experimental validation of SNN accuracy (95%) with public code repository.",
        filename="high_quality_paper.pdf"
    )
    
    # Setup: Create version history with claim
    version_history = test_data_generator.create_version_history(
        filename="high_quality_paper.pdf",
        num_versions=1,
        claim_statuses=['pending_judge_review'],
        claims=[
            {
                "claim_id": "test_quality_001",
                "extracted_claim_text": "SNNs achieve 95% accuracy with 1.2mJ energy per inference",
                "sub_requirement": "Sub-2.1.1"
            }
        ]
    )
    
    # Mock Judge response with quality scores
    mock_judge_response = {
        "verdict": "approved",
        "evidence_quality": {
            "strength_score": 4,
            "strength_rationale": "Strong experimental evidence with quantitative metrics",
            "rigor_score": 5,
            "study_type": "experimental",
            "relevance_score": 4,
            "relevance_notes": "Directly addresses SNN accuracy requirement",
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4,
            "composite_score": 4.2,
            "confidence_level": "high"
        },
        "judge_notes": "Approved. High-quality experimental evidence."
    }
    
    # Execute: Run Judge
    with patch.object(Judge.APIManager, 'cached_api_call') as mock_api:
        mock_api.return_value = mock_judge_response
        
        judge = Judge(
            version_history_file=version_history,
            pillar_definitions_file=test_data_generator.pillar_defs_file
        )
        judge.process_pending_claims()
    
    # Assert: Verify quality scores in version history
    with open(version_history, 'r') as f:
        history = json.load(f)
    
    claim = history["high_quality_paper.pdf"][-1]["review"]["Requirement(s)"][0]
    
    # Check evidence_quality field exists
    assert "evidence_quality" in claim, "Missing evidence_quality field"
    
    quality = claim["evidence_quality"]
    
    # Validate all dimensions present
    assert "strength_score" in quality
    assert "rigor_score" in quality
    assert "relevance_score" in quality
    assert "directness" in quality
    assert "is_recent" in quality
    assert "reproducibility_score" in quality
    assert "composite_score" in quality
    
    # Validate score ranges
    assert 1 <= quality["strength_score"] <= 5
    assert 1 <= quality["rigor_score"] <= 5
    assert 1 <= quality["relevance_score"] <= 5
    assert 1 <= quality["directness"] <= 3
    assert isinstance(quality["is_recent"], bool)
    assert 1 <= quality["reproducibility_score"] <= 5
    assert 1 <= quality["composite_score"] <= 5
    
    # Validate composite score calculation
    expected_composite = (
        quality["strength_score"] * 0.30 +
        quality["rigor_score"] * 0.25 +
        quality["relevance_score"] * 0.25 +
        (quality["directness"] / 3.0) * 0.10 +
        (1.0 if quality["is_recent"] else 0.0) * 0.05 +
        quality["reproducibility_score"] * 0.05
    )
    assert abs(quality["composite_score"] - expected_composite) < 0.1
    
    # Validate approval threshold logic
    # Should approve if: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3
    if claim["status"] == "approved":
        assert quality["composite_score"] >= 3.0
        assert quality["strength_score"] >= 3
        assert quality["relevance_score"] >= 3

@pytest.mark.integration
def test_judge_rejects_low_quality_evidence(temp_workspace, test_data_generator):
    """
    Test that Judge correctly rejects low-quality evidence.
    
    Validates:
    - Low composite score → rejection
    - Low strength but high composite → rejection (threshold logic)
    - Rejection rationale stored
    """
    # Mock low-quality response
    mock_low_quality = {
        "verdict": "rejected",
        "evidence_quality": {
            "strength_score": 2,  # Too low
            "strength_rationale": "Anecdotal evidence without quantitative validation",
            "rigor_score": 2,
            "study_type": "opinion",
            "relevance_score": 3,
            "relevance_notes": "Somewhat relevant but lacks direct evidence",
            "directness": 1,
            "is_recent": False,
            "reproducibility_score": 1,
            "composite_score": 2.1,  # Below threshold
            "confidence_level": "low"
        },
        "judge_notes": "Rejected. Insufficient evidence strength."
    }
    
    # Execute test...
    # Assert rejection with quality scores
```

**2. Test Provenance Tracking**

```python
@pytest.mark.integration
def test_claim_provenance_metadata(temp_workspace, test_data_generator):
    """
    Test that claims include provenance metadata.
    
    Validates:
    - Page numbers present
    - Section names detected
    - Supporting quotes extracted
    - Context preserved
    - Character offsets accurate
    """
    # Setup: Create multi-page test PDF with known sections
    test_pdf = test_data_generator.create_test_pdf_with_sections([
        {"page": 1, "section": "Introduction", "content": "Background on neuromorphic computing..."},
        {"page": 5, "section": "Results", "content": "We achieved 94.3% accuracy on DVS128-Gesture dataset using a 3-layer SNN..."},
        {"page": 6, "section": "Discussion", "content": "This represents a 12x improvement over baseline methods..."}
    ])
    
    # Execute: Extract claims with provenance
    journal_reviewer = JournalReviewer(pdf_file=test_pdf)
    claims = journal_reviewer.extract_claims_with_provenance()
    
    # Assert: Check provenance metadata
    claim = claims[0]  # First claim from Results section
    
    assert "provenance" in claim
    prov = claim["provenance"]
    
    # Validate page numbers
    assert "page_numbers" in prov
    assert isinstance(prov["page_numbers"], list)
    assert 5 in prov["page_numbers"]  # Claim from page 5
    
    # Validate section
    assert prov["section"] == "Results"
    
    # Validate supporting quote
    assert "supporting_quote" in prov
    assert "94.3% accuracy" in prov["supporting_quote"]
    
    # Validate context
    assert "context_before" in prov
    assert "context_after" in prov
    assert len(prov["context_before"]) > 0
    assert len(prov["context_after"]) > 0
    
    # Validate character offsets
    assert "char_start" in prov
    assert "char_end" in prov
    assert prov["char_start"] < prov["char_end"]
```

#### Test Data Modifications

**Update `test_data_generator.py`:**

```python
def create_version_history_with_quality_scores(self, claims_with_scores: List[Dict]) -> str:
    """Create version history with pre-populated evidence quality scores."""
    
    history = {}
    for claim in claims_with_scores:
        filename = claim["filename"]
        if filename not in history:
            history[filename] = []
        
        history[filename].append({
            "version": 1,
            "review": {
                "Requirement(s)": [
                    {
                        "claim_id": claim["claim_id"],
                        "status": claim["status"],
                        "evidence_quality": claim["evidence_quality"],
                        "provenance": claim.get("provenance", {}),
                        "extracted_claim_text": claim["extracted_claim_text"],
                        "sub_requirement": claim["sub_requirement"]
                    }
                ]
            }
        })
    
    history_file = os.path.join(self.temp_dir, "test_version_history.json")
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    return history_file
```

#### Success Criteria Updates

Add to Task Card #6 success criteria:

- [ ] Multi-dimensional evidence quality scores validated
- [ ] Composite score calculation tested
- [ ] Approval threshold logic verified (composite ≥3.0, strength ≥3, relevance ≥3)
- [ ] Low-quality evidence rejection tested
- [ ] Provenance metadata (page numbers, sections, quotes) validated
- [ ] Character offsets accuracy checked
- [ ] Section heading detection tested (>70% accuracy target)

---

### Task Card #7: INT-003 (Version History → CSV Sync)

**Original Scope:** Test that version history syncs correctly to CSV database

**Enhanced Scope:** Add validation that evidence quality scores sync to CSV

#### New Test Cases to Add

**1. Test Evidence Quality Score Sync**

```python
@pytest.mark.integration
def test_quality_scores_sync_to_csv(temp_workspace, test_data_generator):
    """
    Test that evidence quality scores sync from version history to CSV.
    
    Validates:
    - Composite scores added as new CSV column
    - GRADE quality levels synced
    - Provenance metadata preserved (page numbers)
    """
    # Setup: Create version history with quality scores
    version_history = test_data_generator.create_version_history_with_quality_scores([
        {
            "filename": "paper_a.pdf",
            "claim_id": "claim_001",
            "status": "approved",
            "extracted_claim_text": "High quality claim",
            "sub_requirement": "Sub-1.1.1",
            "evidence_quality": {
                "composite_score": 4.2,
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4
            },
            "provenance": {
                "page_numbers": [5, 6],
                "section": "Results"
            }
        }
    ])
    
    # Execute: Sync to CSV
    from sync_history_to_db import sync_version_history_to_csv
    
    csv_file = os.path.join(temp_workspace, "output_database.csv")
    sync_version_history_to_csv(version_history, csv_file)
    
    # Assert: Check CSV has quality columns
    df = pd.read_csv(csv_file)
    
    assert "EVIDENCE_COMPOSITE_SCORE" in df.columns
    assert "EVIDENCE_STRENGTH_SCORE" in df.columns
    assert "EVIDENCE_RIGOR_SCORE" in df.columns
    assert "PROVENANCE_PAGE_NUMBERS" in df.columns
    assert "PROVENANCE_SECTION" in df.columns
    
    # Validate values
    row = df.iloc[0]
    assert row["EVIDENCE_COMPOSITE_SCORE"] == 4.2
    assert row["EVIDENCE_STRENGTH_SCORE"] == 4
    assert row["PROVENANCE_PAGE_NUMBERS"] == "[5, 6]"  # JSON serialized
    assert row["PROVENANCE_SECTION"] == "Results"

@pytest.mark.integration
def test_backward_compatibility_missing_quality_scores(temp_workspace, test_data_generator):
    """
    Test that claims without quality scores sync correctly (backward compatibility).
    
    Legacy claims should get default scores or null values.
    """
    # Setup: Create version history without quality scores (legacy format)
    legacy_history = test_data_generator.create_version_history(
        filename="legacy_paper.pdf",
        num_versions=1,
        claim_statuses=['approved']
    )
    
    # Execute: Sync
    csv_file = os.path.join(temp_workspace, "output_database.csv")
    sync_version_history_to_csv(legacy_history, csv_file)
    
    # Assert: Check backward compatibility
    df = pd.read_csv(csv_file)
    
    # Should have quality columns but with null or default values
    assert "EVIDENCE_COMPOSITE_SCORE" in df.columns
    row = df.iloc[0]
    
    # Either null or default value (3.0)
    assert pd.isna(row["EVIDENCE_COMPOSITE_SCORE"]) or row["EVIDENCE_COMPOSITE_SCORE"] == 3.0
```

#### sync_history_to_db.py Modifications

**Add quality score extraction:**

```python
def extract_quality_scores_from_claim(claim: Dict) -> Dict:
    """Extract evidence quality scores for CSV columns."""
    quality = claim.get("evidence_quality", {})
    provenance = claim.get("provenance", {})
    
    return {
        "EVIDENCE_COMPOSITE_SCORE": quality.get("composite_score"),
        "EVIDENCE_STRENGTH_SCORE": quality.get("strength_score"),
        "EVIDENCE_RIGOR_SCORE": quality.get("rigor_score"),
        "EVIDENCE_RELEVANCE_SCORE": quality.get("relevance_score"),
        "EVIDENCE_DIRECTNESS": quality.get("directness"),
        "EVIDENCE_IS_RECENT": quality.get("is_recent"),
        "EVIDENCE_REPRODUCIBILITY_SCORE": quality.get("reproducibility_score"),
        "STUDY_TYPE": quality.get("study_type"),
        "PROVENANCE_PAGE_NUMBERS": json.dumps(provenance.get("page_numbers")) if provenance.get("page_numbers") else None,
        "PROVENANCE_SECTION": provenance.get("section"),
        "PROVENANCE_QUOTE_PAGE": provenance.get("quote_page")
    }
```

#### Success Criteria Updates

Add to Task Card #7 success criteria:

- [ ] Evidence quality scores sync to CSV correctly
- [ ] All 6 dimensions present in CSV columns
- [ ] Provenance metadata synced (page numbers, sections)
- [ ] Backward compatibility maintained (legacy claims without scores)
- [ ] CSV column names consistent
- [ ] JSON serialization of arrays (page_numbers) works correctly

---

## 🎯 Wave 3 Test Modifications

### Task Card #8: INT-002 (DRA → Orchestrator Flow)

**Original Scope:** Test Deep Requirements Analyzer → Orchestrator integration

**Enhanced Scope:** Add validation of weighted gap analysis using quality scores

#### New Test Cases to Add

**1. Test Weighted Gap Analysis**

```python
@pytest.mark.integration
def test_orchestrator_weighted_gap_analysis(temp_workspace, test_data_generator):
    """
    Test that Orchestrator uses evidence quality scores for gap prioritization.
    
    Validates:
    - Low-quality evidence areas prioritized higher
    - Gap scores calculated using composite scores
    - Prioritization logic (quality → priority)
    """
    # Setup: Create database with varied quality scores
    db = test_data_generator.create_test_database([
        # Sub-req with high-quality evidence (low priority)
        {"sub_req": "Sub-1.1.1", "composite_score": 4.5, "filename": "paper_a.pdf"},
        {"sub_req": "Sub-1.1.1", "composite_score": 4.2, "filename": "paper_b.pdf"},
        
        # Sub-req with low-quality evidence (high priority)
        {"sub_req": "Sub-2.1.1", "composite_score": 2.8, "filename": "paper_c.pdf"},
        {"sub_req": "Sub-2.1.1", "composite_score": 2.5, "filename": "paper_d.pdf"},
        
        # Sub-req with no evidence (highest priority)
        # (Sub-3.1.1 has no entries)
    ])
    
    # Execute: Calculate gap scores
    from Orchestrator import calculate_weighted_gap_score
    
    pillar_defs = test_data_generator.load_pillar_definitions()
    gap_scores = calculate_weighted_gap_score(db, pillar_defs)
    
    # Assert: Prioritization correct
    assert "Sub-1.1.1" in gap_scores
    assert "Sub-2.1.1" in gap_scores
    assert "Sub-3.1.1" in gap_scores
    
    # High quality → low priority
    assert gap_scores["Sub-1.1.1"]["priority"] < 0.5
    assert gap_scores["Sub-1.1.1"]["avg_quality"] > 4.0
    
    # Low quality → high priority
    assert gap_scores["Sub-2.1.1"]["priority"] > 0.7
    assert gap_scores["Sub-2.1.1"]["avg_quality"] < 3.0
    
    # No evidence → highest priority
    assert gap_scores["Sub-3.1.1"]["priority"] == 1.0
    assert gap_scores["Sub-3.1.1"]["avg_quality"] == 0.0
```

#### Success Criteria Updates

Add to Task Card #8:

- [ ] Weighted gap analysis uses composite scores
- [ ] Priority calculation inversely proportional to quality
- [ ] No evidence areas get priority 1.0
- [ ] Low-quality areas prioritized over high-quality
- [ ] Gap analysis report includes quality metrics

---

### Task Card #9: INT-004/005 (Orchestrator Workflow Tests)

**Original Scope:** Test Orchestrator gap analysis and visualization

**Enhanced Scope:** Add validation of temporal coherence analysis (#19) and consensus metadata (#18)

#### New Test Cases to Add

**1. Test Temporal Coherence Analysis**

```python
@pytest.mark.integration
def test_temporal_evolution_analysis(temp_workspace, test_data_generator):
    """
    Test temporal coherence analysis across publication years.
    
    Validates:
    - Publication years extracted
    - Evidence count by year calculated
    - Quality trends detected (improving/stable/declining)
    - Maturity levels assigned correctly
    """
    # Setup: Create database with temporal data
    db = test_data_generator.create_test_database_with_years([
        {"sub_req": "Sub-1.1.1", "year": 2018, "score": 2.5},
        {"sub_req": "Sub-1.1.1", "year": 2020, "score": 3.0},
        {"sub_req": "Sub-1.1.1", "year": 2022, "score": 3.5},
        {"sub_req": "Sub-1.1.1", "year": 2024, "score": 4.0},  # Improving trend
    ])
    
    # Execute: Analyze temporal evolution
    from Orchestrator import analyze_evidence_evolution
    
    pillar_defs = test_data_generator.load_pillar_definitions()
    temporal_analysis = analyze_evidence_evolution(db, pillar_defs)
    
    # Assert: Temporal metrics
    assert "Sub-1.1.1" in temporal_analysis
    analysis = temporal_analysis["Sub-1.1.1"]
    
    assert analysis["earliest_evidence"] == 2018
    assert analysis["latest_evidence"] == 2024
    assert analysis["evidence_span_years"] == 6
    assert analysis["quality_trend"] == "improving"  # Positive slope
    assert analysis["maturity_level"] in ["growing", "established"]
    assert analysis["recent_activity"] == True  # Papers in last 3 years

@pytest.mark.integration
def test_consensus_metadata_tracking(temp_workspace, test_data_generator):
    """
    Test that consensus metadata is tracked and reported.
    
    Validates:
    - Multi-judge consensus metadata stored
    - Agreement rates calculated
    - No-consensus cases flagged
    """
    # Setup: Create version history with consensus metadata
    version_history = test_data_generator.create_version_history_with_consensus([
        {
            "filename": "borderline_paper.pdf",
            "claim_id": "claim_borderline",
            "status": "approved",
            "consensus_metadata": {
                "total_judges": 3,
                "agreement_rate": 0.67,
                "consensus_status": "strong_consensus",
                "vote_breakdown": {"approved": 2, "rejected": 1},
                "average_composite_score": 3.1,
                "score_std_dev": 0.25
            }
        }
    ])
    
    # Execute: Sync and analyze
    csv_file = sync_to_csv(version_history)
    df = pd.read_csv(csv_file)
    
    # Assert: Consensus metadata present
    assert "CONSENSUS_AGREEMENT_RATE" in df.columns
    assert "CONSENSUS_STATUS" in df.columns
    
    row = df.iloc[0]
    assert row["CONSENSUS_AGREEMENT_RATE"] == 0.67
    assert row["CONSENSUS_STATUS"] == "strong_consensus"
```

#### Success Criteria Updates

Add to Task Card #9:

- [ ] Temporal coherence analysis generates correct metrics
- [ ] Quality trends detected with statistical significance (p<0.05)
- [ ] Maturity levels assigned accurately
- [ ] Temporal heatmaps generated successfully
- [ ] Consensus metadata tracked for borderline claims
- [ ] Agreement rates and consensus status validated

---

## 🎯 Wave 4 Test Modifications

### Task Card #10: E2E-001 (Full Pipeline Test)

**Original Scope:** End-to-end test of full literature review pipeline

**Enhanced Scope:** Add validation of complete evidence quality workflow (#16-21)

#### New Test Cases to Add

**1. Test Full Evidence Quality Workflow**

```python
@pytest.mark.e2e
def test_complete_evidence_quality_pipeline(temp_workspace, test_data_generator):
    """
    End-to-end test of evidence quality enhancements.
    
    Validates complete workflow:
    1. Journal-Reviewer extracts claims with provenance
    2. Judge assigns multi-dimensional scores
    3. Borderline claims get consensus review
    4. Orchestrator performs weighted gap analysis
    5. Temporal coherence analysis runs
    6. Evidence triangulation detects clusters
    7. GRADE quality assessment applied
    8. All quality metrics in final CSV
    """
    # Setup: Create realistic test papers
    papers = [
        test_data_generator.create_paper("high_quality_snn.pdf", quality="high"),
        test_data_generator.create_paper("medium_quality_snn.pdf", quality="medium"),
        test_data_generator.create_paper("low_quality_snn.pdf", quality="low"),
        test_data_generator.create_paper("borderline_snn.pdf", quality="borderline")
    ]
    
    # Execute: Run full pipeline
    pipeline = LiteratureReviewPipeline(
        input_papers=papers,
        pillar_definitions=pillar_defs,
        output_dir=temp_workspace
    )
    pipeline.run()
    
    # Assert: Check outputs
    
    # 1. Version history has quality scores
    with open(pipeline.version_history_file) as f:
        history = json.load(f)
    
    for filename, versions in history.items():
        for claim in versions[-1]["review"]["Requirement(s)"]:
            assert "evidence_quality" in claim
            assert "provenance" in claim
            
            # Borderline claims should have consensus metadata
            if 2.5 <= claim["evidence_quality"]["composite_score"] <= 3.5:
                assert "consensus_metadata" in claim
    
    # 2. CSV has all quality columns
    df = pd.read_csv(pipeline.output_csv)
    
    quality_columns = [
        "EVIDENCE_COMPOSITE_SCORE",
        "EVIDENCE_STRENGTH_SCORE",
        "PROVENANCE_PAGE_NUMBERS",
        "GRADE_QUALITY_LEVEL"
    ]
    
    for col in quality_columns:
        assert col in df.columns
    
    # 3. Gap analysis uses weighted scores
    gap_report = pipeline.read_gap_analysis_report()
    assert "weighted_gap_scores" in gap_report
    assert "temporal_analysis" in gap_report
    
    # 4. Triangulation report generated
    triangulation_file = os.path.join(temp_workspace, "triangulation_report.md")
    assert os.path.exists(triangulation_file)
    
    # 5. GRADE summary table exists
    grade_file = os.path.join(temp_workspace, "grade_summary.md")
    assert os.path.exists(grade_file)
```

#### Success Criteria Updates

Add to Task Card #10:

- [ ] Full evidence quality pipeline executes successfully
- [ ] All quality scores present in final outputs
- [ ] Provenance metadata tracked end-to-end
- [ ] Consensus applied to borderline claims
- [ ] Weighted gap analysis uses quality scores
- [ ] Temporal analysis generates heatmaps
- [ ] Triangulation report created
- [ ] GRADE summary table generated
- [ ] Publication-ready systematic review output produced

---

### Task Card #11: E2E-002 (Convergence Test)

**Original Scope:** Test that re-running pipeline produces consistent results

**Enhanced Scope:** Add validation that quality scores remain stable across runs

#### New Test Cases to Add

**1. Test Quality Score Stability**

```python
@pytest.mark.e2e
def test_quality_score_convergence(temp_workspace, test_data_generator):
    """
    Test that evidence quality scores remain stable across pipeline re-runs.
    
    Validates:
    - Composite scores vary by <0.1 across runs
    - Consensus metadata consistent
    - GRADE levels stable
    """
    # Run pipeline twice
    pipeline = LiteratureReviewPipeline(...)
    
    # Run 1
    pipeline.run()
    df1 = pd.read_csv(pipeline.output_csv)
    scores1 = df1["EVIDENCE_COMPOSITE_SCORE"].tolist()
    
    # Run 2 (fresh)
    pipeline.run()
    df2 = pd.read_csv(pipeline.output_csv)
    scores2 = df2["EVIDENCE_COMPOSITE_SCORE"].tolist()
    
    # Assert: Scores stable
    for s1, s2 in zip(scores1, scores2):
        assert abs(s1 - s2) < 0.1  # Allow small variation due to LLM temperature
```

#### Success Criteria Updates

Add to Task Card #11:

- [ ] Quality scores converge across re-runs (variance <0.1)
- [ ] Consensus decisions stable
- [ ] GRADE levels consistent
- [ ] Triangulation clusters reproducible

---

## 📊 Summary of Test Modifications

### Test Coverage by Enhancement

| Enhancement | Test Cards Modified | New Test Cases | Estimated Effort |
|-------------|---------------------|----------------|------------------|
| #16 Multi-Dimensional Scoring | #6, #7, #10, #11 | 4 | 4-6 hours |
| #17 Provenance Tracking | #6, #7, #10 | 3 | 3-4 hours |
| #18 Inter-Rater Reliability | #9, #10, #11 | 3 | 3-4 hours |
| #19 Temporal Coherence | #9, #10 | 2 | 2-3 hours |
| #20 Evidence Triangulation | #10 | 1 | 2-3 hours |
| #21 GRADE Quality | #10 | 1 | 2-3 hours |
| **TOTAL** | **6 task cards** | **14 new tests** | **16-23 hours** |

### Testing Strategy

**Wave 2 (Weeks 3-4):**
- Modify Task Cards #6, #7
- Add scoring and provenance validation
- Effort: 7-10 hours

**Wave 3 (Weeks 5-6):**
- Modify Task Cards #8, #9
- Add temporal and consensus validation
- Effort: 5-7 hours

**Wave 4 (Weeks 7-8):**
- Modify Task Cards #10, #11
- Add full E2E quality workflow validation
- Effort: 4-6 hours

---

## 🔗 Related Documentation

- **Evidence Enhancement Task Cards** - `/task-cards/evidence-enhancement/TASK-*.md`
- **EVIDENCE_ENHANCEMENT_OVERVIEW.md** - High-level enhancement roadmap
- **INTEGRATION_TESTING_TASK_CARDS.md** - Original integration test specifications
- **PARALLEL_DEVELOPMENT_STRATEGY.md** - Wave structure and dependencies

---

**Document Status:** ✅ Ready for Implementation  
**Next Action:** Begin Wave 2 test modifications alongside enhancement implementation  
**Maintainer:** Testing Team  
**Last Updated:** November 13, 2025
