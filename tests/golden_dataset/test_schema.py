"""
Tests for Golden Dataset Schema and Loader

These tests validate the Pydantic models for golden dataset validation
and the loader functionality.
"""

import pytest
from datetime import datetime
from pathlib import Path

from .schema import (
    AnnotatedClaim,
    EvidenceQualityAnnotation,
    ExpectedVerdict,
    KnownGap,
    RecommendationQuality,
    GoldenDataset,
    Verdict,
    ConfidenceLevel
)
from .loader import GoldenDatasetLoader, check_golden_dataset_available


class TestEvidenceQualityAnnotation:
    """Test EvidenceQualityAnnotation model."""
    
    @pytest.mark.unit
    def test_evidence_quality_creation(self):
        """Test creating evidence quality annotation."""
        evidence = EvidenceQualityAnnotation(
            strength_score=4,
            rigor_score=4,
            relevance_score=4,
            directness=3,
            reproducibility_score=4,
            recency_bonus=0.8,
            rationale="Test rationale"
        )
        
        assert evidence.strength_score == 4
        assert evidence.rigor_score == 4
        assert evidence.relevance_score == 4
        assert evidence.directness == 3
        assert evidence.reproducibility_score == 4
        assert evidence.recency_bonus == 0.8
    
    @pytest.mark.unit
    def test_evidence_composite_score(self):
        """Test composite score calculation."""
        evidence = EvidenceQualityAnnotation(
            strength_score=4,
            rigor_score=4,
            relevance_score=4,
            directness=3,
            reproducibility_score=4,
            recency_bonus=0.8,
            rationale="Test"
        )
        
        # Expected: 4*0.30 + 4*0.25 + 4*0.25 + (3/3)*0.10 + 0.8*0.05 + 4*0.05
        # = 1.2 + 1.0 + 1.0 + 0.1 + 0.04 + 0.2 = 3.54
        assert 3.5 <= evidence.composite_score <= 3.6
    
    @pytest.mark.unit
    def test_evidence_score_bounds(self):
        """Test that scores are validated within bounds."""
        with pytest.raises(ValueError):
            EvidenceQualityAnnotation(
                strength_score=6,  # Should be 1-5
                rigor_score=4,
                relevance_score=4,
                directness=3,
                reproducibility_score=4,
                rationale="Test"
            )
    
    @pytest.mark.unit
    def test_directness_bounds(self):
        """Test directness is validated within 1-3."""
        with pytest.raises(ValueError):
            EvidenceQualityAnnotation(
                strength_score=4,
                rigor_score=4,
                relevance_score=4,
                directness=5,  # Should be 1-3
                reproducibility_score=4,
                rationale="Test"
            )


class TestAnnotatedClaim:
    """Test AnnotatedClaim model."""
    
    @pytest.mark.unit
    def test_annotated_claim_creation(self):
        """Test AnnotatedClaim model."""
        claim = AnnotatedClaim(
            claim_id="GD-CLM-0001",
            dataset_version="1.0.0",
            source_paper="test.pdf",
            claim_text="Test claim text for validation",
            evidence_text="Test evidence text for validation",
            correct_pillar="Pillar 1: Test",
            correct_requirement="REQ-T1.1",
            correct_sub_requirement="Sub-1.1.1",
            mapping_rationale="Test rationale",
            expected_verdict=Verdict.APPROVED,
            verdict_rationale="Test verdict rationale",
            verdict_confidence=ConfidenceLevel.HIGH,
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=4,
                rigor_score=4,
                relevance_score=4,
                directness=3,
                reproducibility_score=4,
                rationale="Test evidence rationale"
            ),
            annotator_ids=["test_annotator"],
            annotation_date=datetime.now()
        )
        
        assert claim.claim_id == "GD-CLM-0001"
        assert claim.expected_verdict == Verdict.APPROVED
        assert claim.verdict_confidence == ConfidenceLevel.HIGH
    
    @pytest.mark.unit
    def test_claim_id_pattern(self):
        """Test claim ID pattern validation."""
        with pytest.raises(ValueError):
            AnnotatedClaim(
                claim_id="invalid-id",  # Should match GD-CLM-NNNN
                dataset_version="1.0.0",
                source_paper="test.pdf",
                claim_text="Test claim text for validation",
                evidence_text="Test evidence text for validation",
                correct_pillar="Pillar 1: Test",
                correct_requirement="REQ-T1.1",
                correct_sub_requirement="Sub-1.1.1",
                mapping_rationale="Test rationale",
                expected_verdict=Verdict.APPROVED,
                verdict_rationale="Test verdict rationale",
                verdict_confidence=ConfidenceLevel.HIGH,
                evidence_quality=EvidenceQualityAnnotation(
                    strength_score=4,
                    rigor_score=4,
                    relevance_score=4,
                    directness=3,
                    reproducibility_score=4,
                    rationale="Test evidence rationale"
                ),
                annotator_ids=["test_annotator"],
                annotation_date=datetime.now()
            )
    
    @pytest.mark.unit
    def test_dataset_version_pattern(self):
        """Test dataset version pattern validation."""
        with pytest.raises(ValueError):
            AnnotatedClaim(
                claim_id="GD-CLM-0001",
                dataset_version="invalid",  # Should match X.Y.Z
                source_paper="test.pdf",
                claim_text="Test claim text for validation",
                evidence_text="Test evidence text for validation",
                correct_pillar="Pillar 1: Test",
                correct_requirement="REQ-T1.1",
                correct_sub_requirement="Sub-1.1.1",
                mapping_rationale="Test rationale",
                expected_verdict=Verdict.APPROVED,
                verdict_rationale="Test verdict rationale",
                verdict_confidence=ConfidenceLevel.HIGH,
                evidence_quality=EvidenceQualityAnnotation(
                    strength_score=4,
                    rigor_score=4,
                    relevance_score=4,
                    directness=3,
                    reproducibility_score=4,
                    rationale="Test evidence rationale"
                ),
                annotator_ids=["test_annotator"],
                annotation_date=datetime.now()
            )
    
    @pytest.mark.unit
    def test_claim_with_edge_case(self):
        """Test AnnotatedClaim with edge case flags."""
        claim = AnnotatedClaim(
            claim_id="GD-CLM-0001",
            dataset_version="1.0.0",
            source_paper="test.pdf",
            claim_text="Test claim text for validation",
            evidence_text="Test evidence text for validation",
            correct_pillar="Pillar 1: Test",
            correct_requirement="REQ-T1.1",
            correct_sub_requirement="Sub-1.1.1",
            mapping_rationale="Test rationale",
            expected_verdict=Verdict.BORDERLINE,
            verdict_rationale="Test verdict rationale",
            verdict_confidence=ConfidenceLevel.MEDIUM,
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=3,
                rigor_score=3,
                relevance_score=3,
                directness=2,
                reproducibility_score=3,
                rationale="Test evidence rationale"
            ),
            annotator_ids=["test_annotator"],
            annotation_date=datetime.now(),
            is_edge_case=True,
            edge_case_type="borderline_evidence"
        )
        
        assert claim.is_edge_case is True
        assert claim.edge_case_type == "borderline_evidence"


class TestExpectedVerdict:
    """Test ExpectedVerdict model."""
    
    @pytest.mark.unit
    def test_expected_verdict_creation(self):
        """Test creating expected verdict."""
        verdict = ExpectedVerdict(
            claim_id="GD-CLM-0001",
            expected_verdict=Verdict.APPROVED,
            expected_composite_score_range=(3.5, 4.5),
            expected_strength_range=(4, 5),
            expected_relevance_range=(4, 5),
            true_positive_probability=0.95,
            rejection_reasons=[]
        )
        
        assert verdict.claim_id == "GD-CLM-0001"
        assert verdict.expected_verdict == Verdict.APPROVED
        assert verdict.true_positive_probability == 0.95
    
    @pytest.mark.unit
    def test_expected_verdict_with_rejection_reasons(self):
        """Test expected verdict with rejection reasons."""
        verdict = ExpectedVerdict(
            claim_id="GD-CLM-0002",
            expected_verdict=Verdict.REJECTED,
            expected_composite_score_range=(1.0, 2.0),
            expected_strength_range=(1, 2),
            expected_relevance_range=(2, 4),
            true_positive_probability=0.05,
            rejection_reasons=["Insufficient evidence", "No data"]
        )
        
        assert verdict.expected_verdict == Verdict.REJECTED
        assert len(verdict.rejection_reasons) == 2


class TestKnownGap:
    """Test KnownGap model."""
    
    @pytest.mark.unit
    def test_known_gap_creation(self):
        """Test creating known gap."""
        gap = KnownGap(
            gap_id="GD-GAP-0001",
            dataset_version="0.1.0",
            pillar="Pillar 2: Test",
            requirement_id="REQ-T2.1",
            sub_requirement_id="Sub-2.1.1",
            requirement_text="Test requirement",
            current_completeness=15.0,
            expected_severity="CRITICAL",
            database_state_file="test_state.json",
            why_is_gap="No papers address this."
        )
        
        assert gap.gap_id == "GD-GAP-0001"
        assert gap.expected_severity == "CRITICAL"
        assert gap.current_completeness == 15.0
    
    @pytest.mark.unit
    def test_gap_id_pattern(self):
        """Test gap ID pattern validation."""
        with pytest.raises(ValueError):
            KnownGap(
                gap_id="invalid-gap",  # Should match GD-GAP-NNNN
                dataset_version="0.1.0",
                pillar="Pillar 2: Test",
                requirement_id="REQ-T2.1",
                sub_requirement_id="Sub-2.1.1",
                requirement_text="Test requirement",
                current_completeness=15.0,
                expected_severity="CRITICAL",
                database_state_file="test_state.json",
                why_is_gap="No papers address this."
            )


class TestRecommendationQuality:
    """Test RecommendationQuality model."""
    
    @pytest.mark.unit
    def test_recommendation_quality_creation(self):
        """Test creating recommendation quality."""
        rec = RecommendationQuality(
            gap_id="GD-GAP-0001",
            expected_recommendation_themes=["theme1", "theme2"],
            expected_minimum_rating=4,
            reference_recommendation="Test recommendation"
        )
        
        assert rec.gap_id == "GD-GAP-0001"
        assert len(rec.expected_recommendation_themes) == 2
        assert rec.expected_minimum_rating == 4


class TestGoldenDataset:
    """Test GoldenDataset container model."""
    
    @pytest.mark.unit
    def test_golden_dataset_creation(self):
        """Test creating golden dataset."""
        dataset = GoldenDataset(
            version="1.0.0",
            created_date=datetime.now(),
            last_updated=datetime.now(),
            description="Test dataset",
            annotated_claims=[],
            expected_verdicts=[],
            known_gaps=[],
            recommendation_quality=[]
        )
        
        assert dataset.version == "1.0.0"
        assert dataset.stats["total_claims"] == 0
    
    @pytest.mark.unit
    def test_golden_dataset_stats(self):
        """Test golden dataset statistics calculation."""
        claim1 = AnnotatedClaim(
            claim_id="GD-CLM-0001",
            dataset_version="1.0.0",
            source_paper="test.pdf",
            claim_text="Test claim text for validation",
            evidence_text="Test evidence text for validation",
            correct_pillar="Pillar 1: Test",
            correct_requirement="REQ-T1.1",
            correct_sub_requirement="Sub-1.1.1",
            mapping_rationale="Test rationale",
            expected_verdict=Verdict.APPROVED,
            verdict_rationale="Test verdict rationale",
            verdict_confidence=ConfidenceLevel.HIGH,
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=4,
                rigor_score=4,
                relevance_score=4,
                directness=3,
                reproducibility_score=4,
                rationale="Test evidence rationale"
            ),
            annotator_ids=["test_annotator"],
            annotation_date=datetime.now()
        )
        
        claim2 = AnnotatedClaim(
            claim_id="GD-CLM-0002",
            dataset_version="1.0.0",
            source_paper="test.pdf",
            claim_text="Test claim text for validation",
            evidence_text="Test evidence text for validation",
            correct_pillar="Pillar 1: Test",
            correct_requirement="REQ-T1.1",
            correct_sub_requirement="Sub-1.1.1",
            mapping_rationale="Test rationale",
            expected_verdict=Verdict.REJECTED,
            verdict_rationale="Test verdict rationale",
            verdict_confidence=ConfidenceLevel.HIGH,
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=1,
                rigor_score=1,
                relevance_score=3,
                directness=1,
                reproducibility_score=1,
                rationale="Test evidence rationale"
            ),
            annotator_ids=["test_annotator"],
            annotation_date=datetime.now()
        )
        
        dataset = GoldenDataset(
            version="1.0.0",
            created_date=datetime.now(),
            last_updated=datetime.now(),
            description="Test dataset",
            annotated_claims=[claim1, claim2],
            expected_verdicts=[],
            known_gaps=[],
            recommendation_quality=[]
        )
        
        stats = dataset.stats
        assert stats["total_claims"] == 2
        assert stats["approved_claims"] == 1
        assert stats["rejected_claims"] == 1
        assert stats["borderline_claims"] == 0


class TestGoldenDatasetLoader:
    """Test GoldenDatasetLoader functionality."""
    
    @pytest.mark.unit
    def test_loader_initialization(self):
        """Test loader initialization."""
        loader = GoldenDatasetLoader()
        assert loader.dataset_path.name == "golden_dataset.json"
    
    @pytest.mark.unit
    def test_loader_custom_path(self):
        """Test loader with custom path."""
        custom_path = Path("/tmp/custom_dataset.json")
        loader = GoldenDatasetLoader(dataset_path=custom_path)
        assert loader.dataset_path == custom_path
    
    @pytest.mark.unit
    def test_loader_file_not_found(self):
        """Test loader raises error when file not found."""
        loader = GoldenDatasetLoader(
            dataset_path=Path("/nonexistent/path/dataset.json")
        )
        with pytest.raises(FileNotFoundError):
            loader.load()
    
    @pytest.mark.unit
    def test_loader_with_sample_dataset(self):
        """Test loading the sample dataset."""
        sample_path = Path(__file__).parent / "data" / "golden_dataset_sample.json"
        if not sample_path.exists():
            pytest.skip("Sample dataset not available")
        
        loader = GoldenDatasetLoader(dataset_path=sample_path)
        dataset = loader.load()
        
        assert dataset.version == "0.1.0"
        assert len(dataset.annotated_claims) == 5
        assert len(dataset.expected_verdicts) == 5
        assert len(dataset.known_gaps) == 1
    
    @pytest.mark.unit
    def test_get_claims_by_verdict(self):
        """Test filtering claims by verdict."""
        sample_path = Path(__file__).parent / "data" / "golden_dataset_sample.json"
        if not sample_path.exists():
            pytest.skip("Sample dataset not available")
        
        loader = GoldenDatasetLoader(dataset_path=sample_path)
        loader.load()
        
        approved = loader.get_claims_by_verdict(Verdict.APPROVED)
        rejected = loader.get_claims_by_verdict(Verdict.REJECTED)
        borderline = loader.get_claims_by_verdict(Verdict.BORDERLINE)
        
        assert len(approved) == 2
        assert len(rejected) == 2
        assert len(borderline) == 1
    
    @pytest.mark.unit
    def test_get_edge_cases(self):
        """Test getting edge cases."""
        sample_path = Path(__file__).parent / "data" / "golden_dataset_sample.json"
        if not sample_path.exists():
            pytest.skip("Sample dataset not available")
        
        loader = GoldenDatasetLoader(dataset_path=sample_path)
        loader.load()
        
        edge_cases = loader.get_edge_cases()
        assert len(edge_cases) == 1
        assert edge_cases[0].claim_id == "GD-CLM-0003"
    
    @pytest.mark.unit
    def test_get_claims_for_test(self):
        """Test getting claims for specific test category."""
        sample_path = Path(__file__).parent / "data" / "golden_dataset_sample.json"
        if not sample_path.exists():
            pytest.skip("Sample dataset not available")
        
        loader = GoldenDatasetLoader(dataset_path=sample_path)
        loader.load()
        
        precision_claims = loader.get_claims_for_test("precision")
        assert len(precision_claims) >= 1
    
    @pytest.mark.unit
    def test_validate_dataset(self):
        """Test dataset validation."""
        sample_path = Path(__file__).parent / "data" / "golden_dataset_sample.json"
        if not sample_path.exists():
            pytest.skip("Sample dataset not available")
        
        loader = GoldenDatasetLoader(dataset_path=sample_path)
        loader.load()
        
        validation = loader.validate_dataset()
        # Sample dataset has < 50 claims and < 20 gaps, so it should have issues
        assert "stats" in validation
        assert validation["stats"]["total_claims"] == 5
    
    @pytest.mark.unit
    def test_check_golden_dataset_available(self):
        """Test checking dataset availability."""
        # The default path won't exist unless a full dataset is created
        result = check_golden_dataset_available()
        # Result depends on whether golden_dataset.json exists
        assert isinstance(result, bool)
