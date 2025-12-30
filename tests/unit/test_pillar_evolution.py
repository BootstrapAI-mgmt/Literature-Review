"""Unit tests for pillar evolution system."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from literature_review.analysis.pillar_evolution import (
    PillarEvolutionManager,
    ModificationProposal,
    ProposalStatus,
    ModificationType,
    EvidenceReference,
    ImpactAssessment,
    ReviewComment
)


class TestModificationProposal:
    """Tests for ModificationProposal dataclass."""
    
    def test_create_proposal(self):
        """Test creating a proposal."""
        proposal = ModificationProposal(
            proposal_id="PROP-001",
            title="Test Proposal",
            description="Test description",
            target_pillar="Pillar 1"
        )
        
        assert proposal.proposal_id == "PROP-001"
        assert proposal.status == ProposalStatus.DRAFT
    
    def test_to_dict(self):
        """Test serialization."""
        proposal = ModificationProposal(
            proposal_id="PROP-001",
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            status=ProposalStatus.APPROVED
        )
        
        data = proposal.to_dict()
        assert data["status"] == "approved"
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "proposal_id": "PROP-001",
            "title": "Test",
            "description": "Test",
            "target_pillar": "Pillar 1",
            "status": "under_review",
            "modification_type": "add_validation"
        }
        
        proposal = ModificationProposal.from_dict(data)
        assert proposal.status == ProposalStatus.UNDER_REVIEW
        assert proposal.modification_type == ModificationType.ADD_VALIDATION


class TestEvidenceReference:
    """Tests for EvidenceReference dataclass."""
    
    def test_create_evidence_reference(self):
        """Test creating an evidence reference."""
        evidence = EvidenceReference(
            paper_id="paper-001",
            claim_text="Test claim",
            relevance_score=0.85,
            claim_approved=True
        )
        
        assert evidence.paper_id == "paper-001"
        assert evidence.relevance_score == 0.85
        assert evidence.claim_approved is True
    
    def test_to_dict(self):
        """Test serialization."""
        evidence = EvidenceReference(
            paper_id="paper-001",
            claim_text="Test claim",
            relevance_score=0.75
        )
        
        data = evidence.to_dict()
        assert data["paper_id"] == "paper-001"
        assert data["relevance_score"] == 0.75


class TestImpactAssessment:
    """Tests for ImpactAssessment dataclass."""
    
    def test_create_impact_assessment(self):
        """Test creating an impact assessment."""
        impact = ImpactAssessment(
            affected_requirements=["REQ-1.1", "REQ-1.2"],
            risk_level="medium",
            coverage_change_estimate=-5.0
        )
        
        assert len(impact.affected_requirements) == 2
        assert impact.risk_level == "medium"
        assert impact.coverage_change_estimate == -5.0
    
    def test_to_dict(self):
        """Test serialization."""
        impact = ImpactAssessment(
            affected_requirements=["REQ-1.1"],
            risk_level="high"
        )
        
        data = impact.to_dict()
        assert data["risk_level"] == "high"
        assert data["affected_requirements"] == ["REQ-1.1"]


class TestReviewComment:
    """Tests for ReviewComment dataclass."""
    
    def test_create_review_comment(self):
        """Test creating a review comment."""
        comment = ReviewComment(
            comment_id="CMT-001",
            reviewer="reviewer1",
            timestamp="2025-12-19T12:00:00",
            comment="Test comment",
            decision="approve"
        )
        
        assert comment.reviewer == "reviewer1"
        assert comment.decision == "approve"
    
    def test_to_dict(self):
        """Test serialization."""
        comment = ReviewComment(
            comment_id="CMT-001",
            reviewer="reviewer1",
            timestamp="2025-12-19T12:00:00",
            comment="Test comment"
        )
        
        data = comment.to_dict()
        assert data["reviewer"] == "reviewer1"
        assert data["decision"] is None


class TestPillarEvolutionManager:
    """Tests for PillarEvolutionManager class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1: Sensory": [
                        {"id": "Sub-1.1.1", "text": "Sensory model"}
                    ]
                },
                "validation_criteria": {}
            }
        }
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_gap_analysis(self, tmp_path):
        """Create sample gap analysis."""
        gap = {
            "Pillar 1: Biological Stimulus-Response": {
                "average_completeness": 65,
                "analysis": {
                    "REQ-B1.1: Sensory": {
                        "Sub-1.1.1": {
                            "completeness_percent": 65,
                            "contributing_papers": [
                                {"filename": "paper1.pdf"},
                                {"filename": "paper2.pdf"}
                            ]
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap.json"
        with open(path, 'w') as f:
            json.dump(gap, f)
        
        return str(path)
    
    def test_initialize(self, sample_pillar_definitions):
        """Test manager initialization."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        assert manager.current_version
        assert len(manager.proposals) == 0
    
    def test_generate_proposal(self, sample_pillar_definitions, sample_gap_analysis):
        """Test proposal generation."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        proposal = manager.generate_proposal_from_gap(gap, "Sub-1.1.1")
        
        assert proposal.proposal_id.startswith("PROP-")
        assert proposal.target_pillar == "Pillar 1: Biological Stimulus-Response"
        assert len(proposal.supporting_evidence) == 2
    
    def test_create_custom_proposal(self, sample_pillar_definitions):
        """Test creating a custom proposal."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Add validation",
            description="Test proposal",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="fMRI comparison",
            created_by="test_user"
        )
        
        assert proposal.status == ProposalStatus.DRAFT
        assert proposal.created_by == "test_user"
        assert proposal.applies_to_version == manager.current_version
    
    def test_proposal_workflow(self, sample_pillar_definitions):
        """Test full proposal workflow."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        # Create proposal
        proposal = manager.create_custom_proposal(
            title="Add validation",
            description="Test proposal",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="fMRI comparison"
        )
        
        assert proposal.status == ProposalStatus.DRAFT
        
        # Submit
        proposal = manager.submit_for_review(proposal.proposal_id)
        assert proposal.status == ProposalStatus.PROPOSED
        
        # Start review
        proposal = manager.start_review(proposal.proposal_id, "reviewer1")
        assert proposal.status == ProposalStatus.UNDER_REVIEW
        
        # Approve
        proposal = manager.approve_proposal(proposal.proposal_id, "approver1")
        assert proposal.status == ProposalStatus.APPROVED
    
    def test_apply_proposal(self, sample_pillar_definitions, tmp_path):
        """Test applying a proposal."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Add validation",
            description="Test",
            target_pillar="Pillar 1: Biological",
            target_requirement="Sub-1.1.1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="fMRI comparison >= 0.8"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated_pillar.json")
        original_version = manager.current_version
        definitions, version = manager.apply_proposal(
            proposal.proposal_id, output_path
        )
        
        assert Path(output_path).exists()
        # After applying, the returned version should be the new current version
        assert version == manager.current_version
        
        proposal = manager.proposals[proposal.proposal_id]
        assert proposal.status == ProposalStatus.APPLIED
    
    def test_reject_proposal(self, sample_pillar_definitions):
        """Test rejecting a proposal."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_REQUIREMENT,
            proposed_value="New requirement"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        proposal = manager.reject_proposal(
            proposal.proposal_id, 
            "reviewer", 
            "Not enough evidence"
        )
        
        assert proposal.status == ProposalStatus.REJECTED
        assert len(proposal.review_comments) > 0
    
    def test_impact_assessment(self, sample_pillar_definitions):
        """Test impact assessment."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        # High impact proposal
        proposal = manager.create_custom_proposal(
            title="Remove requirement",
            description="Test",
            target_pillar="Pillar 1",
            target_requirement="REQ-B1.1",
            modification_type=ModificationType.REMOVE_REQUIREMENT,
            proposed_value=""
        )
        
        assert proposal.impact_assessment.risk_level == "high"
    
    def test_save_proposals(self, sample_pillar_definitions, tmp_path):
        """Test saving proposals."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        manager.create_custom_proposal(
            title="Test 1",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.create_custom_proposal(
            title="Test 2",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_METRIC,
            proposed_value="test"
        )
        
        output_path = str(tmp_path / "proposals.json")
        result = manager.save_proposals(output_path)
        
        assert Path(output_path).exists()
        assert result["summary"]["total"] == 2
        assert result["summary"]["draft"] == 2
    
    def test_load_proposals(self, sample_pillar_definitions, tmp_path):
        """Test loading proposals from file."""
        # First create and save proposals
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Test proposal",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test value"
        )
        
        proposals_path = str(tmp_path / "proposals.json")
        manager.save_proposals(proposals_path)
        
        # Load in new manager
        new_manager = PillarEvolutionManager(sample_pillar_definitions, proposals_path)
        
        assert len(new_manager.proposals) == 1
        loaded_proposal = list(new_manager.proposals.values())[0]
        assert loaded_proposal.title == "Test proposal"
    
    def test_get_proposals_by_status(self, sample_pillar_definitions):
        """Test filtering proposals by status."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        # Create proposals with different statuses
        p1 = manager.create_custom_proposal(
            title="Draft 1",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        p2 = manager.create_custom_proposal(
            title="Draft 2",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.submit_for_review(p2.proposal_id)
        
        draft_proposals = manager.get_proposals_by_status(ProposalStatus.DRAFT)
        proposed_proposals = manager.get_proposals_by_status(ProposalStatus.PROPOSED)
        
        assert len(draft_proposals) == 1
        assert len(proposed_proposals) == 1
    
    def test_get_pending_proposals(self, sample_pillar_definitions):
        """Test getting pending proposals."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        
        pending = manager.get_pending_proposals()
        assert len(pending) == 1
    
    def test_get_approved_proposals(self, sample_pillar_definitions):
        """Test getting approved proposals."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        approved = manager.get_approved_proposals()
        assert len(approved) == 1
    
    def test_add_review_comment(self, sample_pillar_definitions):
        """Test adding review comments."""
        manager = PillarEvolutionManager(sample_pillar_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.add_review_comment(
            proposal.proposal_id,
            "reviewer1",
            "Looks good overall"
        )
        
        proposal = manager.proposals[proposal.proposal_id]
        assert len(proposal.review_comments) == 1
        assert proposal.review_comments[0].reviewer == "reviewer1"


class TestWorkflowEdgeCases:
    """Test edge cases in workflow."""
    
    def test_cannot_approve_draft(self, tmp_path):
        """Test that DRAFT proposals cannot be approved directly."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        with pytest.raises(ValueError, match="Cannot approve"):
            manager.approve_proposal(proposal.proposal_id, "admin")
    
    def test_cannot_apply_unapproved(self, tmp_path):
        """Test that unapproved proposals cannot be applied."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        
        with pytest.raises(ValueError, match="Can only apply APPROVED"):
            manager.apply_proposal(proposal.proposal_id)
    
    def test_cannot_submit_non_draft(self, tmp_path):
        """Test that non-DRAFT proposals cannot be submitted."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        
        with pytest.raises(ValueError, match="Can only submit DRAFT"):
            manager.submit_for_review(proposal.proposal_id)
    
    def test_cannot_start_review_non_proposed(self, tmp_path):
        """Test that review can only start on PROPOSED proposals."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        with pytest.raises(ValueError, match="Can only review PROPOSED"):
            manager.start_review(proposal.proposal_id, "reviewer")
    
    def test_cannot_reject_draft(self, tmp_path):
        """Test that DRAFT proposals cannot be rejected."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        with pytest.raises(ValueError, match="Cannot reject"):
            manager.reject_proposal(proposal.proposal_id, "reviewer", "reason")
    
    def test_proposal_not_found(self, tmp_path):
        """Test error when proposal is not found."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        with pytest.raises(ValueError, match="not found"):
            manager.approve_proposal("PROP-NONEXISTENT", "admin")


class TestVersionTracking:
    """Test version tracking functionality."""
    
    def test_version_calculation(self, tmp_path):
        """Test that version is calculated correctly."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        # Version should be a 12-character hash
        assert len(manager.current_version) == 12
        assert all(c in "0123456789abcdef" for c in manager.current_version)
    
    def test_version_changes_on_apply(self, tmp_path):
        """Test that version changes when proposal is applied."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {},
                "validation_criteria": {}
            }
        }
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        original_version = manager.current_version
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            target_requirement="test",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="new validation"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated.json")
        _, new_version = manager.apply_proposal(proposal.proposal_id, output_path)
        
        assert new_version != original_version
        assert len(manager.version_history) == 1
        assert manager.version_history[0]["previous_version"] == original_version
        assert manager.version_history[0]["version"] == new_version
    
    def test_proposal_stores_version(self, tmp_path):
        """Test that proposal stores version information."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        proposal = manager.create_custom_proposal(
            title="Test",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="test"
        )
        
        assert proposal.applies_to_version == manager.current_version


class TestModificationTypes:
    """Test different modification types."""
    
    @pytest.fixture
    def sample_definitions(self, tmp_path):
        """Create sample definitions."""
        definitions = {
            "Pillar 1: Test Pillar": {
                "requirements": {
                    "REQ-1.1: Test Req": [
                        {"id": "Sub-1.1.1", "text": "Original text"}
                    ]
                },
                "validation_criteria": {},
                "quantitative_metrics": {}
            }
        }
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        return str(path)
    
    def test_add_validation(self, sample_definitions, tmp_path):
        """Test ADD_VALIDATION modification."""
        manager = PillarEvolutionManager(sample_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Add validation",
            description="Test",
            target_pillar="Pillar 1",
            target_requirement="Sub-1.1.1",
            modification_type=ModificationType.ADD_VALIDATION,
            proposed_value="fMRI >= 0.8"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated.json")
        definitions, _ = manager.apply_proposal(proposal.proposal_id, output_path)
        
        pillar = definitions["Pillar 1: Test Pillar"]
        assert "Sub-1.1.1" in pillar["validation_criteria"]
        assert pillar["validation_criteria"]["Sub-1.1.1"] == "fMRI >= 0.8"
    
    def test_add_metric(self, sample_definitions, tmp_path):
        """Test ADD_METRIC modification."""
        manager = PillarEvolutionManager(sample_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Add metric",
            description="Test",
            target_pillar="Pillar 1",
            modification_type=ModificationType.ADD_METRIC,
            new_requirement_id="accuracy",
            proposed_value="> 95%"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated.json")
        definitions, _ = manager.apply_proposal(proposal.proposal_id, output_path)
        
        pillar = definitions["Pillar 1: Test Pillar"]
        assert "accuracy" in pillar["quantitative_metrics"]
        assert pillar["quantitative_metrics"]["accuracy"] == "> 95%"
    
    def test_modify_requirement_dict(self, sample_definitions, tmp_path):
        """Test MODIFY_REQUIREMENT with dict format requirements."""
        manager = PillarEvolutionManager(sample_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Modify requirement",
            description="Test",
            target_pillar="Pillar 1",
            target_requirement="Sub-1.1.1",
            modification_type=ModificationType.MODIFY_REQUIREMENT,
            proposed_value="Modified text"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated.json")
        definitions, _ = manager.apply_proposal(proposal.proposal_id, output_path)
        
        pillar = definitions["Pillar 1: Test Pillar"]
        req = pillar["requirements"]["REQ-1.1: Test Req"][0]
        assert req["text"] == "Modified text"
    
    def test_add_requirement(self, sample_definitions, tmp_path):
        """Test ADD_REQUIREMENT modification."""
        manager = PillarEvolutionManager(sample_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Add requirement",
            description="Test",
            target_pillar="Pillar 1",
            target_requirement="REQ-1.1",
            modification_type=ModificationType.ADD_REQUIREMENT,
            proposed_value="",
            new_requirement_id="Sub-1.1.2",
            new_requirement_text="New requirement text"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated.json")
        definitions, _ = manager.apply_proposal(proposal.proposal_id, output_path)
        
        pillar = definitions["Pillar 1: Test Pillar"]
        reqs = pillar["requirements"]["REQ-1.1: Test Req"]
        assert len(reqs) == 2
        assert reqs[1]["id"] == "Sub-1.1.2"
        assert reqs[1]["text"] == "New requirement text"


class TestModifyRequirementStringFormat:
    """Test modification of requirements in string format."""
    
    @pytest.fixture
    def string_format_definitions(self, tmp_path):
        """Create definitions with string format requirements."""
        definitions = {
            "Pillar 1: Test Pillar": {
                "requirements": {
                    "REQ-1.1: Test Req": [
                        "Sub-1.1.1: Original text"
                    ]
                },
                "validation_criteria": {},
                "quantitative_metrics": {}
            }
        }
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        return str(path)
    
    def test_modify_requirement_string(self, string_format_definitions, tmp_path):
        """Test MODIFY_REQUIREMENT with string format requirements."""
        manager = PillarEvolutionManager(string_format_definitions)
        
        proposal = manager.create_custom_proposal(
            title="Modify requirement",
            description="Test",
            target_pillar="Pillar 1",
            target_requirement="Sub-1.1.1",
            modification_type=ModificationType.MODIFY_REQUIREMENT,
            proposed_value="Modified: New text"
        )
        
        manager.submit_for_review(proposal.proposal_id)
        manager.approve_proposal(proposal.proposal_id, "admin")
        
        output_path = str(tmp_path / "updated.json")
        definitions, _ = manager.apply_proposal(proposal.proposal_id, output_path)
        
        pillar = definitions["Pillar 1: Test Pillar"]
        req = pillar["requirements"]["REQ-1.1: Test Req"][0]
        assert req == "Modified: New text"


class TestProposalIdUniqueness:
    """Test that proposal IDs remain unique."""
    
    def test_unique_id_generation(self, tmp_path):
        """Test that proposals get unique IDs even when created in same second."""
        definitions = {"Pillar 1": {"requirements": {}}}
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = PillarEvolutionManager(str(path))
        
        # Create many proposals quickly
        proposals = []
        for i in range(5):
            p = manager.create_custom_proposal(
                title=f"Test {i}",
                description="Test",
                target_pillar="Pillar 1",
                modification_type=ModificationType.ADD_VALIDATION,
                proposed_value=f"test {i}"
            )
            proposals.append(p)
        
        # All IDs should be unique
        ids = [p.proposal_id for p in proposals]
        assert len(ids) == len(set(ids))


class TestGapAnalysisProposal:
    """Test gap analysis-based proposal generation."""
    
    def test_generate_with_different_proposal_types(self, tmp_path):
        """Test generating different proposal types from gap analysis."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1: Sensory": [
                        {"id": "Sub-1.1.1", "text": "Sensory model"}
                    ]
                },
                "validation_criteria": {}
            }
        }
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        gap = {
            "Pillar 1: Biological Stimulus-Response": {
                "average_completeness": 65,
                "analysis": {
                    "REQ-B1.1: Sensory": {
                        "Sub-1.1.1": {
                            "completeness_percent": 65,
                            "contributing_papers": [
                                {"filename": "paper1.pdf"}
                            ]
                        }
                    }
                }
            }
        }
        
        manager = PillarEvolutionManager(str(path))
        
        # Test add_requirement type
        proposal1 = manager.generate_proposal_from_gap(gap, "Sub-1.1.1", "add_requirement")
        assert proposal1.modification_type == ModificationType.ADD_REQUIREMENT
        
        # Test modify_requirement type
        proposal2 = manager.generate_proposal_from_gap(gap, "Sub-1.1.1", "modify_requirement")
        assert proposal2.modification_type == ModificationType.MODIFY_REQUIREMENT
        
        # Test default (add_validation) type
        proposal3 = manager.generate_proposal_from_gap(gap, "Sub-1.1.1")
        assert proposal3.modification_type == ModificationType.ADD_VALIDATION
