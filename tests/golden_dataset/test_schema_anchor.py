"""
Tests for Anchor Paper Schema Extensions

Tests the Pydantic models for exhaustive anchor paper annotation.
"""

import pytest
from datetime import datetime

from tests.golden_dataset.schema_anchor import (
    Extractability,
    DetectionSeverity,
    ClaimLocation,
    ExhaustiveClaim,
    NonExtractionItem,
    AnchorPaper,
    GapScenarioPaper,
    DecoyPaper,
    ExpectedGap,
    ExpectedNonGap,
    GapScenario,
    MatchResult,
    ScenarioResult,
)


class TestExtractability:
    """Tests for Extractability enum."""
    
    def test_extractability_values(self):
        """Test all extractability levels exist."""
        assert Extractability.HIGH.value == "high"
        assert Extractability.MEDIUM.value == "medium"
        assert Extractability.LOW.value == "low"
        assert Extractability.IRRELEVANT.value == "irrelevant"


class TestClaimLocation:
    """Tests for ClaimLocation model."""
    
    def test_claim_location_creation(self):
        """Test creating a claim location."""
        loc = ClaimLocation(page=5, paragraph=2, sentence=1, section="Results")
        assert loc.page == 5
        assert loc.paragraph == 2
        assert loc.sentence == 1
        assert loc.section == "Results"
    
    def test_claim_location_minimal(self):
        """Test creating a claim location with only required fields."""
        loc = ClaimLocation(page=1, paragraph=1)
        assert loc.page == 1
        assert loc.paragraph == 1
        assert loc.sentence is None
        assert loc.section is None
    
    def test_claim_location_validation(self):
        """Test that page and paragraph must be >= 1."""
        with pytest.raises(ValueError):
            ClaimLocation(page=0, paragraph=1)
        with pytest.raises(ValueError):
            ClaimLocation(page=1, paragraph=0)


class TestExhaustiveClaim:
    """Tests for ExhaustiveClaim model."""
    
    def test_exhaustive_claim_creation(self):
        """Test creating an exhaustive claim."""
        claim = ExhaustiveClaim(
            claim_id="AP-001-C01",
            location=ClaimLocation(page=5, paragraph=2),
            exact_text="We achieved 95.2% accuracy on the benchmark.",
            claim_type="quantitative",
            extractability=Extractability.HIGH,
            extractability_rationale="Clear quantitative result in Results section",
            expected_to_be_extracted=True,
            expected_pillar="Pillar 1: Biological Stimulus-Response",
            expected_requirement="REQ-B1.1",
            expected_verdict="approved",
            mapping_confidence="high",
        )
        assert claim.claim_id == "AP-001-C01"
        assert claim.extractability == Extractability.HIGH
        assert claim.expected_to_be_extracted is True
    
    def test_exhaustive_claim_id_pattern(self):
        """Test claim ID pattern validation."""
        # Valid patterns
        ExhaustiveClaim(
            claim_id="AP-001-C01",
            location=ClaimLocation(page=1, paragraph=1),
            exact_text="Test claim text here.",
            claim_type="quantitative",
            extractability=Extractability.HIGH,
            extractability_rationale="Test",
            expected_to_be_extracted=True,
        )
        ExhaustiveClaim(
            claim_id="AP-999-C123",
            location=ClaimLocation(page=1, paragraph=1),
            exact_text="Test claim text here.",
            claim_type="quantitative",
            extractability=Extractability.HIGH,
            extractability_rationale="Test",
            expected_to_be_extracted=True,
        )
        
        # Invalid pattern
        with pytest.raises(ValueError):
            ExhaustiveClaim(
                claim_id="INVALID-ID",
                location=ClaimLocation(page=1, paragraph=1),
                exact_text="Test claim text here.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="Test",
                expected_to_be_extracted=True,
            )


class TestNonExtractionItem:
    """Tests for NonExtractionItem model."""
    
    def test_non_extraction_item_creation(self):
        """Test creating a non-extraction item."""
        item = NonExtractionItem(
            item_id="AP-001-NE-01",
            location=ClaimLocation(page=10, paragraph=4),
            item_text="Future work will explore...",
            item_type="future_work",
            reason_not_relevant="Future work statement, not a current finding",
        )
        assert item.item_id == "AP-001-NE-01"
        assert item.item_type == "future_work"
        assert item.if_extracted_severity == DetectionSeverity.ERROR


class TestAnchorPaper:
    """Tests for AnchorPaper model."""
    
    def test_anchor_paper_creation(self):
        """Test creating an anchor paper."""
        claim = ExhaustiveClaim(
            claim_id="AP-001-C01",
            location=ClaimLocation(page=5, paragraph=2),
            exact_text="We achieved 95.2% accuracy on the benchmark.",
            claim_type="quantitative",
            extractability=Extractability.HIGH,
            extractability_rationale="Clear result",
            expected_to_be_extracted=True,
        )
        
        non_ext = NonExtractionItem(
            item_id="AP-001-NE-01",
            location=ClaimLocation(page=10, paragraph=4),
            item_text="Future work will explore...",
            item_type="future_work",
            reason_not_relevant="Future work",
        )
        
        paper = AnchorPaper(
            paper_id="AP-001",
            source_paper_id="NEURO-001",
            paper_file="paper.pdf",
            title="Test Paper",
            authors=["Author A", "Author B"],
            year=2024,
            venue="NeurIPS",
            domain="neuromorphic",
            page_count=12,
            claim_inventory=[claim],
            non_extraction_items=[non_ext],
            primary_annotator="annotator_001",
            secondary_annotator="annotator_002",
            annotation_date=datetime(2025, 1, 15),
            inter_rater_agreement=0.85,
        )
        
        assert paper.paper_id == "AP-001"
        assert len(paper.claim_inventory) == 1
        assert len(paper.non_extraction_items) == 1
    
    def test_anchor_paper_stats(self):
        """Test anchor paper statistics calculation."""
        claims = [
            ExhaustiveClaim(
                claim_id="AP-001-C01",
                location=ClaimLocation(page=1, paragraph=1),
                exact_text="First claim text here.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="High",
                expected_to_be_extracted=True,
                expected_verdict="approved",
            ),
            ExhaustiveClaim(
                claim_id="AP-001-C02",
                location=ClaimLocation(page=2, paragraph=1),
                exact_text="Second claim text here.",
                claim_type="qualitative",
                extractability=Extractability.MEDIUM,
                extractability_rationale="Medium",
                expected_to_be_extracted=True,
                expected_verdict="rejected",
            ),
            ExhaustiveClaim(
                claim_id="AP-001-C03",
                location=ClaimLocation(page=3, paragraph=1),
                exact_text="Third claim text here.",
                claim_type="methodology",
                extractability=Extractability.LOW,
                extractability_rationale="Low",
                expected_to_be_extracted=False,
                found_by_annotator_a=True,
                found_by_annotator_b=False,
            ),
        ]
        
        paper = AnchorPaper(
            paper_id="AP-001",
            source_paper_id="NEURO-001",
            paper_file="paper.pdf",
            title="Test Paper",
            authors=["Author A"],
            year=2024,
            venue="NeurIPS",
            domain="neuromorphic",
            page_count=12,
            claim_inventory=claims,
            primary_annotator="annotator_001",
            secondary_annotator="annotator_002",
            annotation_date=datetime(2025, 1, 15),
            inter_rater_agreement=0.85,
        )
        
        stats = paper.stats
        assert stats["total_claims"] == 3
        assert stats["high_extractability"] == 1
        assert stats["medium_extractability"] == 1
        assert stats["low_extractability"] == 1
        assert stats["expected_approved"] == 1
        assert stats["expected_rejected"] == 1
        assert stats["both_annotators_found"] == 2
        assert stats["single_annotator_only"] == 1
    
    def test_get_must_find_claims(self):
        """Test filtering must-find claims."""
        claims = [
            ExhaustiveClaim(
                claim_id="AP-001-C01",
                location=ClaimLocation(page=1, paragraph=1),
                exact_text="First claim text here.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="High",
                expected_to_be_extracted=True,
            ),
            ExhaustiveClaim(
                claim_id="AP-001-C02",
                location=ClaimLocation(page=2, paragraph=1),
                exact_text="Second claim text here.",
                claim_type="qualitative",
                extractability=Extractability.LOW,
                extractability_rationale="Low",
                expected_to_be_extracted=False,
            ),
        ]
        
        paper = AnchorPaper(
            paper_id="AP-001",
            source_paper_id="NEURO-001",
            paper_file="paper.pdf",
            title="Test Paper",
            authors=["Author A"],
            year=2024,
            venue="NeurIPS",
            domain="neuromorphic",
            page_count=12,
            claim_inventory=claims,
            primary_annotator="annotator_001",
            secondary_annotator="annotator_002",
            annotation_date=datetime(2025, 1, 15),
            inter_rater_agreement=0.85,
        )
        
        must_find = paper.get_must_find_claims()
        assert len(must_find) == 1
        assert must_find[0].claim_id == "AP-001-C01"


class TestGapScenario:
    """Tests for GapScenario model."""
    
    def test_gap_scenario_creation(self):
        """Test creating a gap scenario."""
        scenario = GapScenario(
            scenario_id="GAP-001",
            scenario_name="STDP Learning Rule Gap",
            scenario_type="iterative",
            initial_papers=[
                GapScenarioPaper(
                    paper_id="NEURO-001",
                    provides_coverage=[{"requirement": "REQ-B1.1", "completeness_contribution": 45}]
                )
            ],
            expected_gaps=[
                ExpectedGap(
                    requirement_id="REQ-B1.4",
                    expected_severity="CRITICAL",
                    expected_completeness=0,
                )
            ],
            expected_non_gaps=[
                ExpectedNonGap(
                    requirement_id="REQ-B1.1",
                    current_completeness=45,
                    reason="45% exceeds gap threshold",
                )
            ],
            decoy_papers=[
                DecoyPaper(
                    paper_id="CLIMATE-001",
                    should_not_close=["REQ-B1.4"],
                    reason="Climate paper, not relevant",
                )
            ],
            designer="designer_001",
            design_date=datetime(2025, 1, 15),
        )
        
        assert scenario.scenario_id == "GAP-001"
        assert scenario.scenario_type == "iterative"
        assert len(scenario.initial_papers) == 1
        assert len(scenario.expected_gaps) == 1
        assert len(scenario.decoy_papers) == 1


class TestMatchResult:
    """Tests for MatchResult model."""
    
    def test_match_result_metrics(self):
        """Test precision/recall calculation."""
        result = MatchResult(
            true_positives=[({"claim_text": "a"}, "AP-001-C01"), ({"claim_text": "b"}, "AP-001-C02")],
            false_positives=[{"claim_text": "c"}],
            false_negatives=["AP-001-C03"],
            acceptable_misses=["AP-001-C04"],
        )
        
        # Precision: 2 / (2 + 1) = 0.667
        assert abs(result.precision - 0.667) < 0.01
        
        # Recall: 2 / (2 + 1) = 0.667
        assert abs(result.recall - 0.667) < 0.01
        
        # F1: 2 * 0.667 * 0.667 / (0.667 + 0.667) = 0.667
        assert abs(result.f1 - 0.667) < 0.01
    
    def test_match_result_empty(self):
        """Test metrics with empty results."""
        result = MatchResult()
        assert result.precision == 0.0
        assert result.recall == 0.0
        assert result.f1 == 0.0


class TestScenarioResult:
    """Tests for ScenarioResult model."""
    
    def test_scenario_result_creation(self):
        """Test creating a scenario result."""
        result = ScenarioResult(
            scenario_id="GAP-001",
            passed=True,
            pass_1_gaps_detected=["REQ-B1.4"],
            pass_1_false_gaps=[],
            pass_1_missed_gaps=[],
            pass_2_severity_changes={"REQ-B1.4": "CRITICAL → MEDIUM"},
            pass_2_decoy_contributions=[],
            failure_reasons=[],
        )
        
        assert result.passed is True
        assert len(result.pass_1_gaps_detected) == 1
        assert len(result.failure_reasons) == 0
