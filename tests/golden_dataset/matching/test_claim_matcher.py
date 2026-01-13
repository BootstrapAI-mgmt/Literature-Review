"""
Tests for Claim Matching Algorithm

Tests the semantic similarity and location-based matching.
"""

import pytest
from tests.golden_dataset.matching.claim_matcher import ClaimMatcher, MatchResult
from tests.golden_dataset.schema_anchor import (
    ExhaustiveClaim,
    ClaimLocation,
    Extractability,
)


class TestMatchResult:
    """Tests for MatchResult dataclass."""
    
    def test_match_result_precision(self):
        """Test precision calculation."""
        result = MatchResult(
            true_positives=[({"claim_text": "a"}, "id1"), ({"claim_text": "b"}, "id2")],
            false_positives=[{"claim_text": "c"}],
        )
        # 2 / (2 + 1) = 0.667
        assert abs(result.precision - 0.667) < 0.01
    
    def test_match_result_recall(self):
        """Test recall calculation."""
        result = MatchResult(
            true_positives=[({"claim_text": "a"}, "id1")],
            false_negatives=["id2", "id3"],
        )
        # 1 / (1 + 2) = 0.333
        assert abs(result.recall - 0.333) < 0.01
    
    def test_match_result_f1(self):
        """Test F1 score calculation."""
        result = MatchResult(
            true_positives=[({"claim_text": "a"}, "id1")],
            false_positives=[{"claim_text": "b"}],
            false_negatives=["id2"],
        )
        # P = 1/2 = 0.5, R = 1/2 = 0.5
        # F1 = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5
        assert abs(result.f1 - 0.5) < 0.01
    
    def test_match_result_empty(self):
        """Test metrics with empty results."""
        result = MatchResult()
        assert result.precision == 0.0
        assert result.recall == 0.0
        assert result.f1 == 0.0


class TestClaimMatcher:
    """Tests for ClaimMatcher class."""
    
    def test_matcher_initialization(self):
        """Test matcher initialization with defaults."""
        matcher = ClaimMatcher()
        assert matcher.threshold == 0.8
        assert matcher.location_tolerance == 1
    
    def test_matcher_custom_threshold(self):
        """Test matcher with custom threshold."""
        matcher = ClaimMatcher(similarity_threshold=0.9)
        assert matcher.threshold == 0.9
    
    def test_sequence_similarity(self):
        """Test sequence-based similarity calculation."""
        matcher = ClaimMatcher(use_semantic=False)
        
        # Identical texts
        sim = matcher._calculate_sequence_similarity("hello world", "hello world")
        assert sim == 1.0
        
        # Similar texts
        sim = matcher._calculate_sequence_similarity("hello world", "hello there")
        assert 0.4 < sim < 0.8
        
        # Different texts
        sim = matcher._calculate_sequence_similarity("hello", "goodbye")
        assert sim < 0.3
    
    def test_match_empty_lists(self):
        """Test matching with empty lists."""
        matcher = ClaimMatcher(use_semantic=False)
        
        result = matcher.match([], [])
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 0
    
    def test_match_empty_extracted(self):
        """Test matching with empty extracted list."""
        matcher = ClaimMatcher(use_semantic=False)
        
        ground_truth = [
            ExhaustiveClaim(
                claim_id="AP-001-C001",
                location=ClaimLocation(page=1, paragraph=1),
                exact_text="This is a test claim.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="High",
                expected_to_be_extracted=True,
            )
        ]
        
        result = matcher.match([], ground_truth)
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 1  # HIGH extractability missed
    
    def test_match_empty_ground_truth(self):
        """Test matching with empty ground truth."""
        matcher = ClaimMatcher(use_semantic=False)
        
        extracted = [{"claim_text": "This is a test."}]
        
        result = matcher.match(extracted, [])
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 1  # All extracted are FP
        assert len(result.false_negatives) == 0
    
    def test_match_identical_claims(self):
        """Test matching identical claims."""
        matcher = ClaimMatcher(use_semantic=False, similarity_threshold=0.8)
        
        ground_truth = [
            ExhaustiveClaim(
                claim_id="AP-001-C001",
                location=ClaimLocation(page=5, paragraph=2),
                exact_text="We achieved 95.2% accuracy on the MNIST benchmark.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="High",
                expected_to_be_extracted=True,
            )
        ]
        
        extracted = [{
            "claim_text": "We achieved 95.2% accuracy on the MNIST benchmark.",
            "source_page": 5
        }]
        
        result = matcher.match(extracted, ground_truth)
        assert len(result.true_positives) == 1
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 0
    
    def test_match_with_location_tolerance(self):
        """Test location-based filtering with tolerance."""
        matcher = ClaimMatcher(use_semantic=False, location_tolerance=1)
        
        ground_truth = [
            ExhaustiveClaim(
                claim_id="AP-001-C001",
                location=ClaimLocation(page=5, paragraph=2),
                exact_text="We achieved 95.2% accuracy on the benchmark.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="High",
                expected_to_be_extracted=True,
            )
        ]
        
        # Within tolerance (page 6, difference of 1)
        extracted_near = [{
            "claim_text": "We achieved 95.2% accuracy on the benchmark.",
            "source_page": 6
        }]
        result = matcher.match(extracted_near, ground_truth)
        assert len(result.true_positives) == 1
        
        # Outside tolerance (page 10, difference of 5)
        extracted_far = [{
            "claim_text": "We achieved 95.2% accuracy on the benchmark.",
            "source_page": 10
        }]
        result = matcher.match(extracted_far, ground_truth)
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 1
    
    def test_match_classifies_by_extractability(self):
        """Test that unmatched claims are classified by extractability."""
        matcher = ClaimMatcher(use_semantic=False, similarity_threshold=0.99)
        
        ground_truth = [
            ExhaustiveClaim(
                claim_id="AP-001-C001",
                location=ClaimLocation(page=1, paragraph=1),
                exact_text="High extractability claim.",
                claim_type="quantitative",
                extractability=Extractability.HIGH,
                extractability_rationale="High",
                expected_to_be_extracted=True,
            ),
            ExhaustiveClaim(
                claim_id="AP-001-C002",
                location=ClaimLocation(page=2, paragraph=1),
                exact_text="Low extractability claim.",
                claim_type="qualitative",
                extractability=Extractability.LOW,
                extractability_rationale="Low",
                expected_to_be_extracted=False,
            ),
        ]
        
        # No matches due to high threshold
        extracted = [{"claim_text": "Completely different text."}]
        
        result = matcher.match(extracted, ground_truth)
        assert "AP-001-C001" in result.false_negatives  # HIGH = false negative
        assert "AP-001-C002" in result.acceptable_misses  # LOW = acceptable miss


class TestClaimMatcherValidation:
    """Tests for anchor paper validation."""
    
    def test_validate_anchor_paper_passing(self):
        """Test validation with good extraction."""
        matcher = ClaimMatcher(use_semantic=False, similarity_threshold=0.7)
        
        from tests.golden_dataset.schema_anchor import AnchorPaper, NonExtractionItem
        from datetime import datetime
        
        claim = ExhaustiveClaim(
            claim_id="AP-001-C001",
            location=ClaimLocation(page=5, paragraph=2),
            exact_text="We achieved 95.2% accuracy on the benchmark.",
            claim_type="quantitative",
            extractability=Extractability.HIGH,
            extractability_rationale="High",
            expected_to_be_extracted=True,
        )
        
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
            claim_inventory=[claim],
            non_extraction_items=[],
            primary_annotator="annotator_001",
            secondary_annotator="annotator_002",
            annotation_date=datetime(2025, 1, 15),
            inter_rater_agreement=0.85,
        )
        
        extracted = [{
            "claim_text": "We achieved 95.2% accuracy on the benchmark.",
            "source_page": 5
        }]
        
        validation = matcher.validate_anchor_paper(extracted, paper)
        assert validation["precision"] == 1.0
        assert validation["recall"] == 1.0
        assert len(validation["non_extraction_violations"]) == 0
        assert validation["passed"] is True
    
    def test_validate_anchor_paper_with_violations(self):
        """Test validation detecting non-extraction violations."""
        matcher = ClaimMatcher(use_semantic=False, similarity_threshold=0.8)
        
        from tests.golden_dataset.schema_anchor import AnchorPaper, NonExtractionItem
        from datetime import datetime
        
        non_ext = NonExtractionItem(
            item_id="AP-001-NE-001",
            location=ClaimLocation(page=10, paragraph=4),
            item_text="Future work will explore advanced methods.",
            item_type="future_work",
            reason_not_relevant="Future work statement",
        )
        
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
            claim_inventory=[],
            non_extraction_items=[non_ext],
            primary_annotator="annotator_001",
            secondary_annotator="annotator_002",
            annotation_date=datetime(2025, 1, 15),
            inter_rater_agreement=0.85,
        )
        
        # Extracted the non-extraction item (violation)
        extracted = [{
            "claim_text": "Future work will explore advanced methods.",
        }]
        
        validation = matcher.validate_anchor_paper(extracted, paper)
        assert len(validation["non_extraction_violations"]) == 1
        assert validation["passed"] is False
