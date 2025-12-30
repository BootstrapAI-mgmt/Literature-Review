"""Unit tests for action generator."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from literature_review.analysis.action_generator import (
    ActionGenerator,
    GeneratedAction,
    ActionChain,
    ActionPriority,
    ActionStatus,
    GeneratorActionVector,
    GeneratorReproducibilityInfo,
    GeneratorResourceRequirements,
    GeneratorChainPosition,
    generate_action_vectors
)
from literature_review.models import ComputeScale


class TestGeneratedAction:
    """Tests for GeneratedAction dataclass."""
    
    def test_create_generated_action(self):
        """Test creating a generated action."""
        action_vector = GeneratorActionVector(
            action_id="test-001",
            description="Test action",
            source_paper_id="paper-001",
            source_claim="Test claim",
            reproducibility=GeneratorReproducibilityInfo(),
            resources=GeneratorResourceRequirements(),
            chain_position=GeneratorChainPosition()
        )
        
        generated = GeneratedAction(
            action_vector=action_vector,
            generation_id="gen-001",
            priority=ActionPriority.HIGH
        )
        
        assert generated.generation_id == "gen-001"
        assert generated.priority == ActionPriority.HIGH
    
    def test_to_dict(self):
        """Test serialization."""
        action_vector = GeneratorActionVector(
            action_id="test-001",
            description="Test action",
            source_paper_id="paper-001",
            source_claim="Test claim",
            reproducibility=GeneratorReproducibilityInfo(),
            resources=GeneratorResourceRequirements(),
            chain_position=GeneratorChainPosition()
        )
        
        generated = GeneratedAction(action_vector=action_vector)
        data = generated.to_dict()
        
        assert "action_vector" in data
        assert "priority" in data
    
    def test_default_values(self):
        """Test default values are set correctly."""
        action_vector = GeneratorActionVector(
            action_id="test-001",
            description="Test action",
            source_paper_id="paper-001",
            source_claim="Test claim"
        )
        
        generated = GeneratedAction(action_vector=action_vector)
        
        assert generated.priority == ActionPriority.MEDIUM
        assert generated.status == ActionStatus.PENDING
        assert generated.complexity_score == 0.5
        assert generated.estimated_hours == 0.0


class TestActionChain:
    """Tests for ActionChain."""
    
    def test_calculate_metrics_empty(self):
        """Test metrics for empty chain."""
        chain = ActionChain(
            chain_id="chain-001",
            name="Test Chain",
            description="Test"
        )
        
        chain.calculate_metrics()
        
        assert chain.total_actions == 0
        assert chain.total_hours == 0
    
    def test_calculate_metrics_with_actions(self):
        """Test metrics with actions."""
        chain = ActionChain(
            chain_id="chain-001",
            name="Test Chain",
            description="Test"
        )
        
        for i in range(3):
            action_vector = GeneratorActionVector(
                action_id=f"test-{i}",
                description=f"Action {i}",
                source_paper_id="paper",
                source_claim="claim",
                reproducibility=GeneratorReproducibilityInfo(),
                resources=GeneratorResourceRequirements(),
                chain_position=GeneratorChainPosition()
            )
            
            generated = GeneratedAction(
                action_vector=action_vector,
                generation_id=f"gen-{i}",
                estimated_hours=4.0,
                status=ActionStatus.COMPLETED if i == 0 else ActionStatus.PENDING
            )
            
            chain.actions.append(generated)
        
        chain.calculate_metrics()
        
        assert chain.total_actions == 3
        assert chain.completed_actions == 1
        assert chain.total_hours == 12.0
    
    def test_to_dict(self):
        """Test chain serialization."""
        chain = ActionChain(
            chain_id="chain-001",
            name="Test Chain",
            description="Test description",
            target_pillar="Pillar 1",
            target_requirement="REQ-1.1"
        )
        
        data = chain.to_dict()
        
        assert data["chain_id"] == "chain-001"
        assert data["name"] == "Test Chain"
        assert data["target_pillar"] == "Pillar 1"
        assert "completion_percentage" in data
    
    def test_critical_path_calculation(self):
        """Test critical path calculation with dependencies."""
        chain = ActionChain(
            chain_id="chain-001",
            name="Test Chain",
            description="Test"
        )
        
        # Create actions with dependencies
        for i in range(3):
            action_vector = GeneratorActionVector(
                action_id=f"test-{i}",
                description=f"Action {i}",
                source_paper_id="paper",
                source_claim="claim"
            )
            
            depends = [f"gen-{i-1}"] if i > 0 else []
            generated = GeneratedAction(
                action_vector=action_vector,
                generation_id=f"gen-{i}",
                estimated_hours=4.0,
                depends_on=depends
            )
            
            chain.actions.append(generated)
        
        chain.calculate_metrics()
        
        # Critical path should be sum of all actions (sequential)
        assert chain.critical_path_hours == 12.0


class TestActionGenerator:
    """Tests for ActionGenerator class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1: Sensory Transduction": [
                        {"id": "Sub-1.1.1", "text": "Sensory model"}
                    ]
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_claims(self):
        """Create sample approved claims."""
        return [
            {
                "claim_id": "claim-001",
                "claim_text": "This architecture achieves 95% accuracy on benchmark",
                "pillar": "Pillar 1",
                "requirement": "REQ-B1.1",
                "requirement_mappings": ["Sub-1.1.1"],
                "approved": True
            },
            {
                "claim_id": "claim-002",
                "claim_text": "The data preprocessing pipeline handles raw signals",
                "pillar": "Pillar 1",
                "requirement": "REQ-B1.1",
                "requirement_mappings": ["Sub-1.1.1"],
                "approved": True
            }
        ]
    
    def test_generate_actions(self, sample_pillar_definitions, sample_claims):
        """Test action generation."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(sample_claims)
        
        assert "summary" in result
        assert result["summary"]["total_actions"] == 2
    
    def test_chain_creation(self, sample_pillar_definitions, sample_claims):
        """Test chain creation."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(sample_claims)
        
        assert len(result["chains"]) == 1
        assert result["chains"][0]["total_actions"] == 2
    
    def test_dependency_ordering(self, sample_pillar_definitions, sample_claims):
        """Test that data claims come before evaluation claims."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(sample_claims)
        
        actions = result["all_actions"]
        
        # Data claim should come first
        assert "data" in actions[0]["action_vector"]["description"].lower() or \
               "preprocess" in actions[0]["action_vector"]["description"].lower()
    
    def test_reproducibility_assessment(self, sample_pillar_definitions):
        """Test reproducibility assessment."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Code available at github.com/example, trained on ImageNet dataset",
            "pillar": "Pillar 1",
            "requirement": "REQ-B1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        repro = action["action_vector"]["reproducibility"]
        
        # Should detect code availability from claim text
        assert repro["code_available"] is True
    
    def test_resource_estimation(self, sample_pillar_definitions):
        """Test resource estimation."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Large-scale distributed training on cluster with PyTorch",
            "pillar": "Pillar 1",
            "requirement": "REQ-B1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        resources = action["action_vector"]["resources"]
        
        # Should detect high compute scale
        assert resources["compute_scale"] == "high"
        assert "PyTorch" in resources["required_libraries"]
    
    def test_save_actions(self, sample_pillar_definitions, sample_claims, tmp_path):
        """Test saving actions to file."""
        generator = ActionGenerator(sample_pillar_definitions)
        generator.generate_actions(sample_claims)
        
        output_path = str(tmp_path / "action_vectors.json")
        result = generator.save_actions(output_path)
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_actions"] == 2
    
    def test_priority_calculation(self, sample_pillar_definitions):
        """Test priority calculation."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Critical for Pillar 1 foundation",
            "pillar": "Pillar 1",
            "requirement": "REQ-B1.1",
            "requirement_mappings": ["Pillar 1"]
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        # Pillar 1 actions should be critical or high priority
        action = result["all_actions"][0]
        assert action["priority"] in ["critical", "high"]
    
    def test_multiple_pillars(self, tmp_path):
        """Test generation with claims from multiple pillars."""
        definitions = {
            "Pillar 1: Test": {"requirements": {}},
            "Pillar 2: Test2": {"requirements": {}}
        }
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        claims = [
            {"claim_text": "Pillar 1 claim", "pillar": "Pillar 1", "requirement": "REQ-1.1"},
            {"claim_text": "Pillar 2 claim", "pillar": "Pillar 2", "requirement": "REQ-2.1"}
        ]
        
        generator = ActionGenerator(str(path))
        result = generator.generate_actions(claims)
        
        assert result["summary"]["total_chains"] == 2
        assert result["summary"]["total_actions"] == 2
    
    def test_empty_claims(self, sample_pillar_definitions):
        """Test handling of empty claims list."""
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions([])
        
        assert result["summary"]["total_actions"] == 0
        assert result["summary"]["total_chains"] == 0


class TestResourceTotals:
    """Tests for resource total calculations."""
    
    def test_resource_aggregation(self, tmp_path):
        """Test that resource totals are aggregated correctly."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {"REQ-1.1": [{"id": "Sub-1.1.1", "text": "Test"}]}
            }
        }
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        claims = [
            {"claim_id": "1", "claim_text": "PyTorch training", "pillar": "Pillar 1", "requirement": "REQ-1.1"},
            {"claim_id": "2", "claim_text": "TensorFlow inference", "pillar": "Pillar 1", "requirement": "REQ-1.1"}
        ]
        
        generator = ActionGenerator(str(path))
        result = generator.generate_actions(claims)
        
        totals = result["resource_totals"]
        
        assert totals["total_gpu_hours"] > 0
        assert "PyTorch" in totals["all_required_libraries"]
        assert "TensorFlow" in totals["all_required_libraries"]


class TestOperationalizationIntegration:
    """Tests for integration with operationalization data."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Test": {"requirements": {}}
        }
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_with_operationalization_data(self, sample_pillar_definitions):
        """Test that operationalization data enhances actions."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Model training approach",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1",
            "paper_id": "paper-001"
        }]
        
        op_data = {
            "paper-001": {
                "code_available": True,
                "code_url": "https://github.com/example",
                "data_available": True,
                "estimated_gpu_hours": 500,
                "memory_gb": 64,
                "libraries": ["PyTorch", "NumPy"]
            }
        }
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims, op_data)
        
        action = result["all_actions"][0]
        
        # Should use operationalization data
        assert action["action_vector"]["reproducibility"]["code_available"] is True
        assert action["action_vector"]["reproducibility"]["reproducibility_score"] > 0.5
        assert action["action_vector"]["resources"]["estimated_gpu_hours"] == 500
        assert "PyTorch" in action["action_vector"]["resources"]["required_libraries"]
    
    def test_fallback_without_operationalization(self, sample_pillar_definitions):
        """Test fallback when operationalization data is not available."""
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Model training approach",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims, None)
        
        # Should still generate actions using heuristics
        assert result["summary"]["total_actions"] == 1


class TestGenerateActionVectorsFunction:
    """Tests for the convenience function."""
    
    def test_generate_action_vectors(self, tmp_path):
        """Test the convenience function."""
        definitions = {
            "Pillar 1: Test": {"requirements": {}}
        }
        
        pillar_path = tmp_path / "pillar.json"
        with open(pillar_path, 'w') as f:
            json.dump(definitions, f)
        
        claims = [{
            "claim_id": "claim-001",
            "claim_text": "Test claim",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        output_path = str(tmp_path / "action_vectors.json")
        
        result = generate_action_vectors(
            pillar_definitions_path=str(pillar_path),
            approved_claims=claims,
            output_path=output_path
        )
        
        assert Path(output_path).exists()
        assert result["summary"]["total_actions"] == 1


class TestHoursEstimation:
    """Tests for hours estimation."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {"Pillar 1: Test": {"requirements": {}}}
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_novel_claim_increases_hours(self, sample_pillar_definitions):
        """Test that novel claims have higher hour estimates."""
        claims = [{
            "claim_text": "Novel new architecture design for inference",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        # Novel claims should have higher hours (16 = 8 * 2)
        assert action["estimated_hours"] >= 16.0
    
    def test_simple_claim_decreases_hours(self, sample_pillar_definitions):
        """Test that simple claims have lower hour estimates."""
        claims = [{
            "claim_text": "Simple straightforward implementation",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        # Simple claims should have lower hours (4 = 8 * 0.5)
        assert action["estimated_hours"] <= 4.0


class TestComplexityScoring:
    """Tests for complexity scoring."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {"Pillar 1: Test": {"requirements": {}}}
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_complex_claim_high_score(self, sample_pillar_definitions):
        """Test that complex claims have higher complexity scores."""
        claims = [{
            "claim_text": "Complex sophisticated advanced neural network",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        assert action["complexity_score"] > 0.5
    
    def test_simple_claim_low_score(self, sample_pillar_definitions):
        """Test that simple claims have lower complexity scores."""
        claims = [{
            "claim_text": "Simple basic standard implementation",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        action = result["all_actions"][0]
        assert action["complexity_score"] < 0.5


class TestPriorityBreakdown:
    """Tests for priority breakdown."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {"Pillar 1: Test": {"requirements": {}}}
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_priority_breakdown_structure(self, sample_pillar_definitions):
        """Test that priority breakdown has correct structure."""
        claims = [{
            "claim_text": "Test claim",
            "pillar": "Pillar 1",
            "requirement": "REQ-1.1"
        }]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        breakdown = result["priority_breakdown"]
        
        # Should have at least one action in breakdown
        total = sum(len(actions) for actions in breakdown.values())
        assert total == 1


class TestChainDependencies:
    """Tests for chain dependencies."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {"Pillar 1: Test": {"requirements": {}}}
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_predecessor_successor_links(self, sample_pillar_definitions):
        """Test that predecessor/successor links are set correctly."""
        claims = [
            {"claim_text": "First data preprocessing", "pillar": "Pillar 1", "requirement": "REQ-1.1"},
            {"claim_text": "Second model training", "pillar": "Pillar 1", "requirement": "REQ-1.1"},
            {"claim_text": "Third evaluation benchmark", "pillar": "Pillar 1", "requirement": "REQ-1.1"}
        ]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        actions = result["all_actions"]
        
        # First action should have no predecessor
        assert actions[0]["action_vector"]["chain_position"]["predecessor_id"] is None
        # First action should have successor
        assert actions[0]["action_vector"]["chain_position"]["successor_id"] is not None
        
        # Last action should have no successor
        assert actions[-1]["action_vector"]["chain_position"]["successor_id"] is None
    
    def test_blocks_list_updated(self, sample_pillar_definitions):
        """Test that blocks list is updated for sequential actions."""
        claims = [
            {"claim_text": "First action", "pillar": "Pillar 1", "requirement": "REQ-1.1"},
            {"claim_text": "Second action", "pillar": "Pillar 1", "requirement": "REQ-1.1"}
        ]
        
        generator = ActionGenerator(sample_pillar_definitions)
        result = generator.generate_actions(claims)
        
        actions = result["all_actions"]
        
        # First action should block second
        assert len(actions[0]["blocks"]) == 1
        assert actions[1]["generation_id"] == actions[0]["blocks"][0]
