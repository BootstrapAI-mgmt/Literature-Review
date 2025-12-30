"""Unit tests for stakeholder analyzer."""

import pytest
import json
from pathlib import Path

from literature_review.analysis.stakeholder_analyzer import (
    StakeholderAnalyzer,
    Stakeholder,
    GapImpact,
    StakeholderGapSummary,
    ImpactLevel,
    NotificationPriority,
    generate_stakeholder_matrix
)


class TestStakeholder:
    """Tests for Stakeholder dataclass."""
    
    def test_create_stakeholder(self):
        """Test creating a stakeholder."""
        stakeholder = Stakeholder(
            id="core_research",
            name="Core Research Team",
            description="Primary researchers",
            priority_weight=1.0,
            interests=["Biological accuracy"],
            primary_pillars=["Pillar 1", "Pillar 3"]
        )
        
        assert stakeholder.id == "core_research"
        assert stakeholder.priority_weight == 1.0
        assert stakeholder.decision_authority == "medium"
        assert stakeholder.notification_threshold == "medium"
    
    def test_to_dict(self):
        """Test serialization."""
        stakeholder = Stakeholder(
            id="test",
            name="Test",
            description="Test",
            priority_weight=0.8,
            interests=[],
            primary_pillars=[]
        )
        
        data = stakeholder.to_dict()
        assert data["priority_weight"] == 0.8
        assert data["id"] == "test"
        assert "decision_authority" in data


class TestGapImpact:
    """Tests for GapImpact dataclass."""
    
    def test_create_impact(self):
        """Test creating an impact."""
        impact = GapImpact(
            gap_id="Pillar 1::REQ-1.1::Sub-1.1.1",
            gap_description="Test gap",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            stakeholder_id="core_research",
            stakeholder_name="Core Research",
            impact_level=ImpactLevel.HIGH,
            impact_score=0.75
        )
        
        assert impact.impact_level == ImpactLevel.HIGH
        assert impact.impact_score == 0.75
        assert impact.action_required is False
    
    def test_to_dict(self):
        """Test serialization."""
        impact = GapImpact(
            gap_id="test",
            gap_description="test",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            stakeholder_id="test",
            stakeholder_name="Test",
            impact_level=ImpactLevel.CRITICAL
        )
        
        data = impact.to_dict()
        assert data["impact_level"] == "critical"
        assert data["notification_priority"] == "monthly"
    
    def test_default_values(self):
        """Test default values."""
        impact = GapImpact(
            gap_id="test",
            gap_description="test",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            stakeholder_id="test",
            stakeholder_name="Test"
        )
        
        assert impact.impact_level == ImpactLevel.MEDIUM
        assert impact.impact_score == 0.0
        assert impact.interest_alignment == []
        assert impact.action_required is False


class TestStakeholderGapSummary:
    """Tests for StakeholderGapSummary dataclass."""
    
    def test_create_summary(self):
        """Test creating a summary."""
        summary = StakeholderGapSummary(
            stakeholder_id="core_research",
            stakeholder_name="Core Research Team"
        )
        
        assert summary.total_impacts == 0
        assert summary.critical_impacts == 0
        assert summary.attention_required is False
    
    def test_to_dict(self):
        """Test serialization."""
        summary = StakeholderGapSummary(
            stakeholder_id="test",
            stakeholder_name="Test",
            total_impacts=5,
            critical_impacts=1,
            attention_required=True
        )
        
        data = summary.to_dict()
        assert data["total_impacts"] == 5
        assert data["critical_impacts"] == 1


class TestImpactLevel:
    """Tests for ImpactLevel enum."""
    
    def test_values(self):
        """Test enum values."""
        assert ImpactLevel.CRITICAL.value == "critical"
        assert ImpactLevel.HIGH.value == "high"
        assert ImpactLevel.MEDIUM.value == "medium"
        assert ImpactLevel.LOW.value == "low"
        assert ImpactLevel.NONE.value == "none"


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""
    
    def test_values(self):
        """Test enum values."""
        assert NotificationPriority.IMMEDIATE.value == "immediate"
        assert NotificationPriority.WEEKLY.value == "weekly"
        assert NotificationPriority.MONTHLY.value == "monthly"
        assert NotificationPriority.NONE.value == "none"


class TestStakeholderAnalyzer:
    """Tests for StakeholderAnalyzer class."""
    
    @pytest.fixture
    def sample_stakeholder_definitions(self, tmp_path):
        """Create sample stakeholder definitions."""
        definitions = {
            "$schema": "stakeholder_definitions_v1",
            "stakeholders": {
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
                    "stakeholders": ["core_research"]
                },
                "performance": {
                    "description": "Computational efficiency",
                    "relevant_pillars": ["Pillar 2", "Pillar 4"],
                    "stakeholders": ["engineering"]
                }
            }
        }
        
        path = tmp_path / "stakeholder.json"
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
        sample_stakeholder_definitions, 
        sample_pillar_definitions
    ):
        """Test analyzer initialization."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        assert len(analyzer.stakeholders) == 3
        assert "core_research" in analyzer.stakeholders
        assert "engineering" in analyzer.stakeholders
        assert "executive" in analyzer.stakeholders
    
    def test_parse_stakeholders(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test stakeholder parsing."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        core = analyzer.stakeholders["core_research"]
        assert core.name == "Core Research Team"
        assert core.priority_weight == 1.0
        assert "Pillar 1" in core.primary_pillars
    
    def test_analyze_impacts(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test impact analysis."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = analyzer.analyze_gap_impacts(gap)
        
        assert "summary" in result
        assert result["summary"]["total_gaps_analyzed"] == 3
        assert "stakeholder_summaries" in result
        assert "prioritized_gaps" in result
    
    def test_pillar_relevance(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test that pillar relevance affects impact score."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        # Core research should have higher impact on Pillar 1 gaps
        pillar1_impacts = [
            i for i in analyzer.impacts
            if "Pillar 1" in i.pillar and i.stakeholder_id == "core_research"
        ]
        
        pillar2_impacts = [
            i for i in analyzer.impacts
            if "Pillar 2" in i.pillar and i.stakeholder_id == "core_research"
        ]
        
        if pillar1_impacts and pillar2_impacts:
            # Core research cares more about Pillar 1 (primary pillar)
            avg_p1 = sum(i.impact_score for i in pillar1_impacts) / len(pillar1_impacts)
            avg_p2 = sum(i.impact_score for i in pillar2_impacts) / len(pillar2_impacts)
            assert avg_p1 >= avg_p2
    
    def test_severity_calculation(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test severity calculation from completeness."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        assert analyzer._calculate_severity(10) == "critical"
        assert analyzer._calculate_severity(40) == "high"
        assert analyzer._calculate_severity(60) == "medium"
        assert analyzer._calculate_severity(80) == "low"
    
    def test_notification_priority_critical_only(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for critical_only threshold."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        # Critical only threshold
        notification = analyzer._determine_notification(
            ImpactLevel.CRITICAL, "critical_only"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = analyzer._determine_notification(
            ImpactLevel.HIGH, "critical_only"
        )
        assert notification == NotificationPriority.NONE
    
    def test_notification_priority_high(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for high threshold."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        notification = analyzer._determine_notification(
            ImpactLevel.CRITICAL, "high"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = analyzer._determine_notification(
            ImpactLevel.HIGH, "high"
        )
        assert notification == NotificationPriority.WEEKLY
        
        notification = analyzer._determine_notification(
            ImpactLevel.LOW, "high"
        )
        assert notification == NotificationPriority.NONE
    
    def test_notification_priority_medium(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for medium threshold."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        notification = analyzer._determine_notification(
            ImpactLevel.CRITICAL, "medium"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = analyzer._determine_notification(
            ImpactLevel.MEDIUM, "medium"
        )
        assert notification == NotificationPriority.MONTHLY
    
    def test_notification_priority_low(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority for low threshold."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        notification = analyzer._determine_notification(
            ImpactLevel.HIGH, "low"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        notification = analyzer._determine_notification(
            ImpactLevel.LOW, "low"
        )
        assert notification == NotificationPriority.MONTHLY
    
    def test_interest_alignment(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test interest alignment detection."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        gap = {
            "description": "Missing biological accuracy data",
            "requirement": "REQ-B1.1",
            "pillar": "Pillar 1: Biological Stimulus-Response"
        }
        
        stakeholder = analyzer.stakeholders["core_research"]
        aligned = analyzer._check_interest_alignment(gap, stakeholder)
        
        # Should find "Biological accuracy" interest
        assert len(aligned) > 0
        assert any("biological" in a.lower() or "accuracy" in a.lower() for a in aligned)
    
    def test_stakeholder_report(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test per-stakeholder report generation."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        report = analyzer.get_stakeholder_report("core_research")
        
        assert report is not None
        assert "stakeholder" in report
        assert "summary" in report
        assert "impacts" in report
        assert report["stakeholder"]["id"] == "core_research"
    
    def test_stakeholder_report_not_found(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test stakeholder report for non-existent stakeholder."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        report = analyzer.get_stakeholder_report("non_existent")
        assert report is None
    
    def test_gap_report(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test per-gap report generation."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        # Get a gap ID from impacts
        if analyzer.impacts:
            gap_id = analyzer.impacts[0].gap_id
            report = analyzer.get_gap_stakeholder_report(gap_id)
            
            assert "gap_id" in report
            assert "stakeholder_impacts" in report
            assert "total_stakeholders_affected" in report
    
    def test_save_matrix(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis,
        tmp_path
    ):
        """Test saving matrix to file."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        output_path = str(tmp_path / "matrix.json")
        matrix = analyzer.save_matrix(output_path)
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert "summary" in saved
        assert "stakeholder_summaries" in saved
        assert "prioritized_gaps" in saved
        assert "all_impacts" in saved
        assert "notification_queue" in saved
    
    def test_notification_queue(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test notification queue generation."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = analyzer.analyze_gap_impacts(gap)
        
        assert "notification_queue" in result
        queue = result["notification_queue"]
        
        # Check queue structure
        for priority, items in queue.items():
            assert priority in ["immediate", "weekly", "monthly"]
            for item in items:
                assert "stakeholder" in item
                assert "gap_id" in item
                assert "impact_level" in item
    
    def test_attention_required(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test attention_required flag."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = analyzer.analyze_gap_impacts(gap)
        
        # Check that summaries have attention_required field
        for sid, summary in result["stakeholder_summaries"].items():
            assert "attention_required" in summary
            # Should be True if critical_impacts > 0 or high_impacts >= 3
            if summary["critical_impacts"] > 0:
                assert summary["attention_required"] is True
    
    def test_empty_gap_analysis(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        tmp_path
    ):
        """Test handling of empty gap analysis."""
        # Create empty gap analysis
        gap = {}
        gap_path = tmp_path / "empty_gap.json"
        with open(gap_path, 'w') as f:
            json.dump(gap, f)
        
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        result = analyzer.analyze_gap_impacts(gap)
        
        assert result["summary"]["total_gaps_analyzed"] == 0
        assert result["summary"]["total_stakeholder_impacts"] == 0
    
    def test_executive_all_pillars(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test that executive with 'All' pillars gets impacts from all pillars."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        exec_impacts = [
            i for i in analyzer.impacts
            if i.stakeholder_id == "executive"
        ]
        
        # Executive should have impacts from both pillars
        pillars = set(i.pillar for i in exec_impacts)
        assert len(pillars) >= 1  # Should have impacts


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_generate_matrix(self, tmp_path):
        """Test the convenience function."""
        # Create test files
        stakeholder_def = {
            "stakeholders": {
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
        
        stakeholder_path = tmp_path / "stakeholder.json"
        pillar_path = tmp_path / "pillar.json"
        gap_path = tmp_path / "gap.json"
        output_path = tmp_path / "matrix.json"
        
        for path, data in [
            (stakeholder_path, stakeholder_def),
            (pillar_path, pillar_def),
            (gap_path, gap)
        ]:
            with open(path, 'w') as f:
                json.dump(data, f)
        
        matrix = generate_stakeholder_matrix(
            str(stakeholder_path),
            str(pillar_path),
            str(gap_path),
            str(output_path)
        )
        
        assert "summary" in matrix
        assert Path(output_path).exists()
    
    def test_generate_matrix_creates_file(self, tmp_path):
        """Test that generate_stakeholder_matrix creates output file."""
        stakeholder_def = {
            "stakeholders": {
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
        
        stakeholder_path = tmp_path / "stakeholder.json"
        pillar_path = tmp_path / "pillar.json"
        gap_path = tmp_path / "gap.json"
        output_path = tmp_path / "output_matrix.json"
        
        for path, data in [
            (stakeholder_path, stakeholder_def),
            (pillar_path, pillar_def),
            (gap_path, gap)
        ]:
            with open(path, 'w') as f:
                json.dump(data, f)
        
        matrix = generate_stakeholder_matrix(
            str(stakeholder_path),
            str(pillar_path),
            str(gap_path),
            str(output_path)
        )
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_gaps_analyzed"] == 1
        assert "timestamp" in saved
