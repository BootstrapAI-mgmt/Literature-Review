"""Unit tests for operationalization data models."""

import pytest
from datetime import datetime

from literature_review.models import (
    ActionVector,
    ActionType,
    EffortLevel,
    ResourceRequirements,
    ReproducibilityInfo,
    ActionChainPosition,
    generate_action_id,
    ValidationStrategy,
    ValidationStatus,
    EvidenceType,
    BenchmarkLink,
    MetricDefinition
)


class TestActionVector:
    """Tests for ActionVector dataclass."""
    
    def test_create_basic_action_vector(self):
        """Test creating a basic action vector."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2: AI Stimulus-Response",
            requirement_id="REQ-A2.1",
            action_description="Implement DVS sensor integration"
        )
        
        assert av.action_id == "AV-P2-001"
        assert av.pillar == "Pillar 2: AI Stimulus-Response"
        assert av.action_type == ActionType.IMPLEMENT
        assert av.status == "pending"
    
    def test_reproducibility_score_calculation(self):
        """Test reproducibility score calculation."""
        repro = ReproducibilityInfo(
            code_available=True,
            data_available=True,
            hyperparameters_specified=True,
            methodology_detail_level="high"
        )
        
        assert repro.reproducibility_score == 1.0
    
    def test_reproducibility_score_partial(self):
        """Test partial reproducibility score."""
        repro = ReproducibilityInfo(
            code_available=True,
            data_available=False,
            hyperparameters_specified=False,
            methodology_detail_level="low"
        )
        
        assert repro.reproducibility_score == 0.35
    
    def test_action_vector_to_dict(self):
        """Test serialization to dictionary."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2",
            requirement_id="REQ-A2.1",
            action_description="Test action",
            source_papers=["paper1.pdf", "paper2.pdf"]
        )
        
        data = av.to_dict()
        
        assert data["action_id"] == "AV-P2-001"
        assert data["source_papers"] == ["paper1.pdf", "paper2.pdf"]
        assert "is_actionable" in data
        assert "is_reproducible" in data
    
    def test_action_vector_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "action_id": "AV-P2-001",
            "pillar": "Pillar 2",
            "requirement_id": "REQ-A2.1",
            "action_type": "validate",
            "action_description": "Test action",
            "evidence_strength": 0.85
        }
        
        av = ActionVector.from_dict(data)
        
        assert av.action_id == "AV-P2-001"
        assert av.action_type == ActionType.VALIDATE
        assert av.evidence_strength == 0.85
    
    def test_is_actionable_true(self):
        """Test actionable check when no blockers."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2",
            requirement_id="REQ-A2.1"
        )
        
        assert av.is_actionable is True
    
    def test_is_actionable_false_with_unknowns(self):
        """Test actionable check when blocking unknowns exist."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2",
            requirement_id="REQ-A2.1",
            chain_position=ActionChainPosition(
                blocking_unknowns=["What hardware to use?"]
            )
        )
        
        assert av.is_actionable is False


class TestGenerateActionId:
    """Tests for action ID generation."""
    
    def test_generate_basic_id(self):
        """Test basic ID generation."""
        action_id = generate_action_id(
            pillar="Pillar 2: AI Stimulus-Response",
            requirement_id="REQ-A2.1",
            sequence=1
        )
        
        assert action_id.startswith("AV-P2-")
        assert action_id.endswith("-001")
    
    def test_generate_sequential_ids(self):
        """Test sequential ID generation."""
        id1 = generate_action_id("Pillar 2", "REQ-A2.1", 1)
        id2 = generate_action_id("Pillar 2", "REQ-A2.1", 2)
        
        assert id1 != id2
        assert id1.endswith("-001")
        assert id2.endswith("-002")


class TestValidationStrategy:
    """Tests for ValidationStrategy dataclass."""
    
    def test_create_basic_strategy(self):
        """Test creating a basic validation strategy."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1"
        )
        
        assert vs.requirement_id == "Sub-1.1.1"
        assert vs.status == ValidationStatus.NO_STRATEGY
        assert vs.is_strategy_defined is False
    
    def test_strategy_defined_with_method(self):
        """Test is_strategy_defined with method."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            validation_method="fMRI comparison"
        )
        
        assert vs.is_strategy_defined is True
    
    def test_is_fully_validated(self):
        """Test fully validated check."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            validation_method="fMRI comparison",
            status=ValidationStatus.VALIDATED,
            evidence_papers=["paper1.pdf"],
            minimum_evidence_count=1
        )
        
        assert vs.is_fully_validated is True
    
    def test_serialization_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            validation_method="fMRI comparison",
            required_evidence_types=[EvidenceType.EXPERIMENTAL]
        )
        
        data = vs.to_dict()
        vs2 = ValidationStrategy.from_dict(data)
        
        assert vs.requirement_id == vs2.requirement_id
        assert vs.validation_method == vs2.validation_method


class TestBenchmarkLink:
    """Tests for BenchmarkLink dataclass."""
    
    def test_create_benchmark_link(self):
        """Test creating a benchmark link."""
        bl = BenchmarkLink(
            benchmark_name="DVS128 Gesture",
            benchmark_type="dataset",
            metric_measured="accuracy",
            measurement_method="Top-1 classification accuracy"
        )
        
        assert bl.benchmark_name == "DVS128 Gesture"
        assert bl.benchmark_type == "dataset"
    
    def test_serialization(self):
        """Test serialization."""
        bl = BenchmarkLink(
            benchmark_name="N-MNIST",
            benchmark_type="dataset",
            metric_measured="inference_time",
            measurement_method="Wall-clock time"
        )
        
        data = bl.to_dict()
        
        assert data["benchmark_name"] == "N-MNIST"
        assert data["benchmark_type"] == "dataset"


class TestMetricDefinition:
    """Tests for MetricDefinition dataclass."""
    
    def test_create_metric_with_benchmarks(self):
        """Test creating a metric with benchmarks."""
        md = MetricDefinition(
            metric_id="P2-M1",
            metric_name="latency_target",
            target_value="< 10ms end-to-end",
            measurement_method="End-to-end timing",
            benchmarks=[
                BenchmarkLink(
                    benchmark_name="DVS128 Gesture",
                    benchmark_type="dataset",
                    metric_measured="latency",
                    measurement_method="Wall-clock time"
                )
            ],
            benchmark_status="covered"
        )
        
        assert md.metric_name == "latency_target"
        assert len(md.benchmarks) == 1
        assert md.benchmark_status == "covered"
