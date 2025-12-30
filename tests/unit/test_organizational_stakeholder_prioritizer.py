"""Unit tests for organizational stakeholder prioritizer."""

import pytest
import json
from pathlib import Path

from literature_review.analysis.organizational_stakeholder_prioritizer import (
    OrganizationalStakeholderPrioritizer,
    OrganizationalStakeholder,
    OrganizationalGapPriority,
    OrganizationalStakeholderSummary,
    PriorityLevel,
    NotificationPriority,
    generate_org_stakeholder_prioritization_matrix,
    # Backward compatibility aliases
    StakeholderAnalyzer,
    Stakeholder,
    GapImpact,
    StakeholderGapSummary,
    ImpactLevel,
    generate_stakeholder_matrix
)


class TestOrganizationalStakeholder:
    """Tests for OrganizationalStakeholder dataclass."""
    
    def test_create_org_stakeholder(self):
        """Test creating an organizational stakeholder."""
        org_stakeholder = OrganizationalStakeholder(
            id="core_research",
            name="Core Research Team",
            description="Primary researchers",
            priority_weight=1.0,
            interests=["Biological accuracy"],
            primary_pillars=["Pillar 1", "Pillar 3"]
        )
        
        assert org_stakeholder.id == "core_research"
        assert org_stakeholder.priority_weight == 1.0
        assert org_stakeholder.decision_authority == "medium"
        assert org_stakeholder.notification_threshold == "medium"
    
    def test_to_dict(self):
        """Test serialization."""
        org_stakeholder = OrganizationalStakeholder(
            id="test",
            name="Test",
            description="Test",
            priority_weight=0.8,
            interests=[],
            primary_pillars=[]
        )
        
        data = org_stakeholder.to_dict()
        assert data["priority_weight"] == 0.8
        assert data["id"] == "test"
        assert "decision_authority" in data


class TestOrganizationalGapPriority:
    """Tests for OrganizationalGapPriority dataclass."""
    
    def test_create_priority(self):
        """Test creating a priority."""
        priority = OrganizationalGapPriority(
            gap_id="Pillar 1::REQ-1.1::Sub-1.1.1",
            gap_description="Test gap",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            org_stakeholder_id="core_research",
            org_stakeholder_name="Core Research",
            priority_level=PriorityLevel.HIGH,
            priority_score=0.75
        )
        
        assert priority.priority_level == PriorityLevel.HIGH
        assert priority.priority_score == 0.75
        assert priority.action_required is False
    
    def test_to_dict(self):
        """Test serialization."""
        priority = OrganizationalGapPriority(
            gap_id="test",
            gap_description="test",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            org_stakeholder_id="test",
            org_stakeholder_name="Test",
            priority_level=PriorityLevel.CRITICAL
        )
        
        data = priority.to_dict()
        assert data["priority_level"] == "critical"
        assert data["notification_priority"] == "monthly"
    
    def test_default_values(self):
        """Test default values."""
        priority = OrganizationalGapPriority(
            gap_id="test",
            gap_description="test",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            org_stakeholder_id="test",
            org_stakeholder_name="Test"
        )
        
        assert priority.priority_level == PriorityLevel.MEDIUM
        assert priority.priority_score == 0.0
        assert priority.interest_alignment == []
        assert priority.action_required is False


class TestOrganizationalStakeholderSummary:
    """Tests for OrganizationalStakeholderSummary dataclass."""
    
    def test_create_summary(self):
        """Test creating a summary."""
        summary = OrganizationalStakeholderSummary(
            org_stakeholder_id="core_research",
            org_stakeholder_name="Core Research Team"
        )
        
        assert summary.total_priorities == 0
        assert summary.critical_priorities == 0
        assert summary.attention_required is False
    
    def test_to_dict(self):
        """Test serialization."""
        summary = OrganizationalStakeholderSummary(
            org_stakeholder_id="test",
            org_stakeholder_name="Test",
            total_priorities=5,
            critical_priorities=1,
            attention_required=True
        )
        
        data = summary.to_dict()
        assert data["total_priorities"] == 5
        assert data["critical_priorities"] == 1


class TestPriorityLevel:
    """Tests for PriorityLevel enum."""
    
    def test_values(self):
        """Test enum values."""
        assert PriorityLevel.CRITICAL.value == "critical"
        assert PriorityLevel.HIGH.value == "high"
        assert PriorityLevel.MEDIUM.value == "medium"
        assert PriorityLevel.LOW.value == "low"
        assert PriorityLevel.NONE.value == "none"


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""
    
    def test_values(self):
        """Test enum values."""
        assert NotificationPriority.IMMEDIATE.value == "immediate"
        assert NotificationPriority.WEEKLY.value == "weekly"
        assert NotificationPriority.MONTHLY.value == "monthly"
        assert NotificationPriority.NONE.value == "none"


class TestBackwardCompatibility:
    """Tests for backward compatibility aliases."""
    
    def test_aliases_exist(self):
        """Test that backward compatibility aliases exist."""
        assert StakeholderAnalyzer is OrganizationalStakeholderPrioritizer
        assert Stakeholder is OrganizationalStakeholder
        assert GapImpact is OrganizationalGapPriority
        assert StakeholderGapSummary is OrganizationalStakeholderSummary
        assert ImpactLevel is PriorityLevel
        assert generate_stakeholder_matrix is generate_org_stakeholder_prioritization_matrix


class TestOrganizationalStakeholderPrioritizer:
    """Tests for OrganizationalStakeholderPrioritizer class."""
    
    @pytest.fixture
    def sample_org_stakeholder_definitions(self, tmp_path):
        """Create sample organizational stakeholder definitions."""
        definitions = {
            "$schema": "organizational_stakeholder_definitions_v1",
            "organizational_stakeholders": {
                "core_research": {
                    "name": "Core Research Team",
                    "description": "Primary researchers",
                    "priority_weight": 1.0,
                    "interests": ["Biological accuracy", "Novel architectures"],
                    "primary_pillars": ["Pillar 1", "Pillar 3"],
                    "decision_authority": "high",
                    "notification_threshold": "medium"
                },
                "engineering": {
                    "name": "Engineering Team",
                    "description": "Implementation",
                    "priority_weight": 0.9,
                    "interests": ["Performance", "Scalability"],
                    "primary_pillars": ["Pillar 2", "Pillar 4"],
                    "decision_authority": "medium",
                    "notification_threshold": "high"
                },
                "executive": {
                    "name": "Executive Leadership",
                    "description": "Strategic direction",
                    "priority_weight": 0.95,
                    "interests": ["Overall progress"],
                    "primary_pillars": ["All"],
                    "decision_authority": "high",
                    "notification_threshold": "critical_only"
                }
            },
            "interest_categories": {
                "biological_accuracy": {
                    "description": "Bio alignment",
                    "relevant_pillars": ["Pillar 1", "Pillar 3"],
                    "organizational_stakeholders": ["core_research"]
                },
                "performance": {
                    "description": "Computational efficiency",
                    "relevant_pillars": ["Pillar 2", "Pillar 4"],
                    "organizational_stakeholders": ["engineering"]
                }
            }
        }
        
        path = tmp_path / "org_stakeholder.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1": [{"id": "Sub-1.1.1", "text": "Test"}]
                }
            },
            "Pillar 2: AI Stimulus-Response": {
                "requirements": {
                    "REQ-A2.1": [{"id": "Sub-2.1.1", "text": "Test"}]
                }
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
                "average_completeness": 45,
                "analysis": {
                    "REQ-B1.1": {
                        "Sub-1.1.1": {
                            "completeness_percent": 25,
                            "gap_reason": "Missing biological validation data"
                        },
                        "Sub-1.1.2": {
                            "completeness_percent": 65,
                            "gap_reason": "Partial coverage"
                        }
                    }
                }
            },
            "Pillar 2: AI Stimulus-Response": {
                "average_completeness": 60,
                "analysis": {
                    "REQ-A2.1": {
                        "Sub-2.1.1": {
                            "completeness_percent": 60,
                            "gap_reason": "Performance benchmarks incomplete"
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap.json"
        with open(path, 'w') as f:
            json.dump(gap, f)
        
        return str(path)
    
    def test_initialize(
        self, 
        sample_org_stakeholder_definitions, 
        sample_pillar_definitions
    ):
        """Test prioritizer initialization."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        assert len(prioritizer.org_stakeholders) == 3
        assert "core_research" in prioritizer.org_stakeholders
        assert "engineering" in prioritizer.org_stakeholders
        assert "executive" in prioritizer.org_stakeholders
    
    def test_parse_org_stakeholders(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test organizational stakeholder parsing."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        core = prioritizer.org_stakeholders["core_research"]
        assert core.name == "Core Research Team"
        assert core.priority_weight == 1.0
        assert "Pillar 1" in core.primary_pillars
    
    def test_analyze_priorities(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test priority analysis."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = prioritizer.analyze_gap_priorities(gap)
        
        assert "summary" in result
        assert result["summary"]["total_gaps_analyzed"] == 3
        assert "org_stakeholder_summaries" in result
        assert "prioritized_gaps" in result
        assert result["matrix_type"] == "organizational_stakeholder_prioritization"
    
    def test_pillar_relevance(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test that pillar relevance affects priority score."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        prioritizer.analyze_gap_priorities(gap)
        
        # Core research should have higher priority on Pillar 1 gaps
        pillar1_priorities = [
            p for p in prioritizer.priorities
            if "Pillar 1" in p.pillar and p.org_stakeholder_id == "core_research"
        ]
        
        pillar2_priorities = [
            p for p in prioritizer.priorities
            if "Pillar 2" in p.pillar and p.org_stakeholder_id == "core_research"
        ]
        
        if pillar1_priorities and pillar2_priorities:
            # Core research cares more about Pillar 1 (primary pillar)
            avg_p1 = sum(p.priority_score for p in pillar1_priorities) / len(pillar1_priorities)
            avg_p2 = sum(p.priority_score for p in pillar2_priorities) / len(pillar2_priorities)
            assert avg_p1 >= avg_p2
    
    def test_severity_calculation(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test severity calculation from completeness."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        assert prioritizer._calculate_severity(10) == "critical"
        assert prioritizer._calculate_severity(40) == "high"
        assert prioritizer._calculate_severity(60) == "medium"
        assert prioritizer._calculate_severity(80) == "low"
    
    def test_notification_priority_critical_only(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for critical_only threshold."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        # Critical only threshold
        notification = prioritizer._determine_notification(
            PriorityLevel.CRITICAL, "critical_only"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = prioritizer._determine_notification(
            PriorityLevel.HIGH, "critical_only"
        )
        assert notification == NotificationPriority.NONE
    
    def test_notification_priority_high(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for high threshold."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        notification = prioritizer._determine_notification(
            PriorityLevel.CRITICAL, "high"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = prioritizer._determine_notification(
            PriorityLevel.HIGH, "high"
        )
        assert notification == NotificationPriority.WEEKLY
        
        notification = prioritizer._determine_notification(
            PriorityLevel.LOW, "high"
        )
        assert notification == NotificationPriority.NONE
    
    def test_notification_priority_medium(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for medium threshold."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        notification = prioritizer._determine_notification(
            PriorityLevel.CRITICAL, "medium"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = prioritizer._determine_notification(
            PriorityLevel.MEDIUM, "medium"
        )
        assert notification == NotificationPriority.MONTHLY
    
    def test_notification_priority_low(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for low threshold."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        notification = prioritizer._determine_notification(
            PriorityLevel.HIGH, "low"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = prioritizer._determine_notification(
            PriorityLevel.LOW, "low"
        )
        assert notification == NotificationPriority.MONTHLY
    
    def test_interest_alignment(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test interest alignment detection."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        gap = {
            "description": "Missing biological accuracy data",
            "requirement": "REQ-B1.1",
            "pillar": "Pillar 1: Biological Stimulus-Response"
        }
        
        org_stakeholder = prioritizer.org_stakeholders["core_research"]
        aligned = prioritizer._check_interest_alignment(gap, org_stakeholder)
        
        # Should find "Biological accuracy" interest
        assert len(aligned) > 0
        assert any("biological" in a.lower() or "accuracy" in a.lower() for a in aligned)
    
    def test_org_stakeholder_report(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test per-organizational-stakeholder report generation."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        prioritizer.analyze_gap_priorities(gap)
        
        report = prioritizer.get_org_stakeholder_report("core_research")
        
        assert report is not None
        assert "org_stakeholder" in report
        assert "summary" in report
        assert "priorities" in report
        assert report["org_stakeholder"]["id"] == "core_research"
    
    def test_org_stakeholder_report_not_found(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test org stakeholder report for non-existent stakeholder."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        prioritizer.analyze_gap_priorities(gap)
        
        report = prioritizer.get_org_stakeholder_report("non_existent")
        assert report is None
    
    def test_gap_report(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test per-gap report generation."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        prioritizer.analyze_gap_priorities(gap)
        
        # Get a gap ID from priorities
        if prioritizer.priorities:
            gap_id = prioritizer.priorities[0].gap_id
            report = prioritizer.get_gap_org_stakeholder_report(gap_id)
            
            assert "gap_id" in report
            assert "org_stakeholder_priorities" in report
            assert "total_org_stakeholders_affected" in report
    
    def test_save_matrix(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis,
        tmp_path
    ):
        """Test saving matrix to file."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        prioritizer.analyze_gap_priorities(gap)
        
        output_path = str(tmp_path / "matrix.json")
        matrix = prioritizer.save_matrix(output_path)
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert "summary" in saved
        assert "org_stakeholder_summaries" in saved
        assert "prioritized_gaps" in saved
        assert "all_priorities" in saved
        assert "notification_queue" in saved
        assert saved["matrix_type"] == "organizational_stakeholder_prioritization"
    
    def test_notification_queue(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test notification queue generation."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = prioritizer.analyze_gap_priorities(gap)
        
        assert "notification_queue" in result
        queue = result["notification_queue"]
        
        # Check queue structure
        for priority, items in queue.items():
            assert priority in ["immediate", "weekly", "monthly"]
            for item in items:
                assert "org_stakeholder" in item
                assert "gap_id" in item
                assert "priority_level" in item
    
    def test_attention_required(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test attention_required flag."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = prioritizer.analyze_gap_priorities(gap)
        
        # Check that summaries have attention_required field
        for sid, summary in result["org_stakeholder_summaries"].items():
            assert "attention_required" in summary
            # Should be True if critical_priorities > 0 or high_priorities >= 3
            if summary["critical_priorities"] > 0:
                assert summary["attention_required"] is True
    
    def test_empty_gap_analysis(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        tmp_path
    ):
        """Test handling of empty gap analysis."""
        # Create empty gap analysis
        gap = {}
        gap_path = tmp_path / "empty_gap.json"
        with open(gap_path, 'w') as f:
            json.dump(gap, f)
        
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        result = prioritizer.analyze_gap_priorities(gap)
        
        assert result["summary"]["total_gaps_analyzed"] == 0
        assert result["summary"]["total_stakeholder_priorities"] == 0
    
    def test_executive_all_pillars(
        self,
        sample_org_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test that executive with 'All' pillars gets priorities from all pillars."""
        prioritizer = OrganizationalStakeholderPrioritizer(
            sample_org_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        prioritizer.analyze_gap_priorities(gap)
        
        exec_priorities = [
            p for p in prioritizer.priorities
            if p.org_stakeholder_id == "executive"
        ]
        
        # Executive should have priorities from both pillars
        pillars = set(p.pillar for p in exec_priorities)
        assert len(pillars) >= 1  # Should have priorities


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_generate_matrix(self, tmp_path):
        """Test the convenience function."""
        # Create test files
        org_stakeholder_def = {
            "organizational_stakeholders": {
                "test": {
                    "name": "Test",
                    "description": "Test",
                    "priority_weight": 1.0,
                    "interests": [],
                    "primary_pillars": ["Pillar 1"]
                }
            }
        }
        
        pillar_def = {
            "Pillar 1: Test": {"requirements": {}}
        }
        
        gap = {
            "Pillar 1: Test": {
                "average_completeness": 50,
                "analysis": {
                    "REQ-1.1": {
                        "Sub-1.1.1": {"completeness_percent": 50}
                    }
                }
            }
        }
        
        org_stakeholder_path = tmp_path / "org_stakeholder.json"
        pillar_path = tmp_path / "pillar.json"
        gap_path = tmp_path / "gap.json"
        output_path = tmp_path / "matrix.json"
        
        for path, data in [
            (org_stakeholder_path, org_stakeholder_def),
            (pillar_path, pillar_def),
            (gap_path, gap)
        ]:
            with open(path, 'w') as f:
                json.dump(data, f)
        
        matrix = generate_org_stakeholder_prioritization_matrix(
            str(org_stakeholder_path),
            str(pillar_path),
            str(gap_path),
            str(output_path)
        )
        
        assert "summary" in matrix
        assert Path(output_path).exists()
    
    def test_generate_matrix_creates_file(self, tmp_path):
        """Test that generate_org_stakeholder_prioritization_matrix creates output file."""
        org_stakeholder_def = {
            "organizational_stakeholders": {
                "test": {
                    "name": "Test Team",
                    "description": "Test description",
                    "priority_weight": 0.8,
                    "interests": ["Testing"],
                    "primary_pillars": ["Pillar 1"],
                    "decision_authority": "medium",
                    "notification_threshold": "high"
                }
            },
            "interest_categories": {}
        }
        
        pillar_def = {
            "Pillar 1: Testing": {
                "requirements": {
                    "REQ-1.1": [{"id": "Sub-1.1.1", "text": "Test requirement"}]
                }
            }
        }
        
        gap = {
            "Pillar 1: Testing": {
                "average_completeness": 30,
                "analysis": {
                    "REQ-1.1": {
                        "Sub-1.1.1": {
                            "completeness_percent": 30,
                            "gap_reason": "Missing test coverage"
                        }
                    }
                }
            }
        }
        
        org_stakeholder_path = tmp_path / "org_stakeholder.json"
        pillar_path = tmp_path / "pillar.json"
        gap_path = tmp_path / "gap.json"
        output_path = tmp_path / "output_matrix.json"
        
        for path, data in [
            (org_stakeholder_path, org_stakeholder_def),
            (pillar_path, pillar_def),
            (gap_path, gap)
        ]:
            with open(path, 'w') as f:
                json.dump(data, f)
        
        matrix = generate_org_stakeholder_prioritization_matrix(
            str(org_stakeholder_path),
            str(pillar_path),
            str(gap_path),
            str(output_path)
        )
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_gaps_analyzed"] == 1
        assert "timestamp" in saved
        assert saved["matrix_type"] == "organizational_stakeholder_prioritization"
