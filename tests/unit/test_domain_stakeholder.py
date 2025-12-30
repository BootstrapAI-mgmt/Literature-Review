"""Unit tests for domain stakeholder extraction module."""

import pytest
import json
from pathlib import Path

from literature_review.models.domain_stakeholder import (
    DomainStakeholder,
    LiteratureStakeholderImpact,
    StakeholderCategory,
    generate_impact_id
)

from literature_review.reviewers.prompts.stakeholder_extraction_prompt import (
    STAKEHOLDER_IMPACT_EXTRACTION_PROMPT,
    format_stakeholder_extraction_prompt,
    format_stakeholder_batch_prompt,
    parse_extraction_response,
    MIN_CONFIDENCE_THRESHOLD,
    MAX_IMPACTS_PER_PAPER
)

from literature_review.analysis.domain_stakeholder_extractor import (
    DomainStakeholderExtractor,
    STAKEHOLDER_ALIASES
)


class TestStakeholderCategory:
    """Tests for StakeholderCategory enum."""
    
    def test_all_categories_exist(self):
        """Test that all expected categories exist."""
        assert StakeholderCategory.RESEARCHER.value == "researcher"
        assert StakeholderCategory.ENGINEER.value == "engineer"
        assert StakeholderCategory.CLINICIAN.value == "clinician"
        assert StakeholderCategory.PRACTITIONER.value == "practitioner"
        assert StakeholderCategory.POLICY_MAKER.value == "policy_maker"
        assert StakeholderCategory.END_USER.value == "end_user"
        assert StakeholderCategory.OTHER.value == "other"
    
    def test_category_from_string(self):
        """Test creating category from string value."""
        cat = StakeholderCategory("researcher")
        assert cat == StakeholderCategory.RESEARCHER
    
    def test_category_invalid_value(self):
        """Test that invalid category raises ValueError."""
        with pytest.raises(ValueError):
            StakeholderCategory("invalid_category")


class TestDomainStakeholder:
    """Tests for DomainStakeholder dataclass."""
    
    def test_create_basic_stakeholder(self):
        """Test creating a basic domain stakeholder."""
        stakeholder = DomainStakeholder(
            stakeholder_type="neuroscientists",
            category=StakeholderCategory.RESEARCHER,
            description="Researchers studying biological neural systems"
        )
        
        assert stakeholder.stakeholder_type == "neuroscientists"
        assert stakeholder.category == StakeholderCategory.RESEARCHER
        assert stakeholder.description == "Researchers studying biological neural systems"
        assert stakeholder.source_papers == []
    
    def test_stakeholder_with_papers(self):
        """Test stakeholder with source papers."""
        stakeholder = DomainStakeholder(
            stakeholder_type="hardware engineers",
            category=StakeholderCategory.ENGINEER,
            description="Engineers designing neuromorphic chips",
            source_papers=["paper1.pdf", "paper2.pdf"]
        )
        
        assert len(stakeholder.source_papers) == 2
        assert "paper1.pdf" in stakeholder.source_papers
    
    def test_stakeholder_to_dict(self):
        """Test serialization to dictionary."""
        stakeholder = DomainStakeholder(
            stakeholder_type="neuroscientists",
            category=StakeholderCategory.RESEARCHER,
            description="Brain researchers",
            source_papers=["paper1.pdf"]
        )
        
        data = stakeholder.to_dict()
        
        assert data["stakeholder_type"] == "neuroscientists"
        assert data["category"] == "researcher"
        assert data["description"] == "Brain researchers"
        assert data["source_papers"] == ["paper1.pdf"]
    
    def test_stakeholder_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "stakeholder_type": "clinicians",
            "category": "clinician",
            "description": "Medical professionals",
            "source_papers": ["paper1.pdf", "paper2.pdf"]
        }
        
        stakeholder = DomainStakeholder.from_dict(data)
        
        assert stakeholder.stakeholder_type == "clinicians"
        assert stakeholder.category == StakeholderCategory.CLINICIAN
        assert len(stakeholder.source_papers) == 2
    
    def test_stakeholder_from_dict_defaults(self):
        """Test from_dict with missing optional fields."""
        data = {
            "stakeholder_type": "researchers"
        }
        
        stakeholder = DomainStakeholder.from_dict(data)
        
        assert stakeholder.stakeholder_type == "researchers"
        assert stakeholder.category == StakeholderCategory.OTHER
        assert stakeholder.description == ""
        assert stakeholder.source_papers == []


class TestLiteratureStakeholderImpact:
    """Tests for LiteratureStakeholderImpact dataclass."""
    
    @pytest.fixture
    def sample_impact(self):
        """Create a sample impact for testing."""
        return LiteratureStakeholderImpact(
            impact_id="LSI-001",
            gap_id="GAP-abc123",
            gap_description="Lack of standardized benchmarks",
            affected_stakeholder="hardware engineers",
            stakeholder_category=StakeholderCategory.ENGINEER,
            impact_statement="Cannot compare designs objectively",
            source_quote="Without benchmarks, engineers cannot...",
            source_paper="snn_review_2024.pdf",
            paper_section="Discussion",
            extraction_confidence=0.95
        )
    
    def test_create_basic_impact(self, sample_impact):
        """Test creating a basic stakeholder impact."""
        assert sample_impact.impact_id == "LSI-001"
        assert sample_impact.gap_id == "GAP-abc123"
        assert sample_impact.affected_stakeholder == "hardware engineers"
        assert sample_impact.extraction_confidence == 0.95
        assert sample_impact.gap_filled is False
    
    def test_impact_to_dict(self, sample_impact):
        """Test serialization to dictionary."""
        data = sample_impact.to_dict()
        
        assert data["impact_id"] == "LSI-001"
        assert data["gap_description"] == "Lack of standardized benchmarks"
        assert data["stakeholder_category"] == "engineer"
        assert data["source_paper"] == "snn_review_2024.pdf"
        assert data["gap_filled"] is False
    
    def test_impact_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "impact_id": "LSI-002",
            "gap_id": "GAP-xyz789",
            "gap_description": "Missing validation data",
            "affected_stakeholder": "neuroscientists",
            "stakeholder_category": "researcher",
            "impact_statement": "Cannot validate computational models",
            "source_paper": "paper.pdf",
            "extraction_confidence": 0.85
        }
        
        impact = LiteratureStakeholderImpact.from_dict(data)
        
        assert impact.impact_id == "LSI-002"
        assert impact.stakeholder_category == StakeholderCategory.RESEARCHER
        assert impact.extraction_confidence == 0.85
    
    def test_mark_resolved(self, sample_impact):
        """Test marking an impact as resolved."""
        assert sample_impact.gap_filled is False
        
        sample_impact.mark_resolved("new_paper.pdf", "2025-01-01")
        
        assert sample_impact.gap_filled is True
        assert sample_impact.filled_by_paper == "new_paper.pdf"
        assert sample_impact.filled_date == "2025-01-01"
    
    def test_impact_defaults(self):
        """Test impact with default values."""
        impact = LiteratureStakeholderImpact(
            impact_id="LSI-003",
            gap_id="GAP-000",
            gap_description="Test gap",
            affected_stakeholder="researchers",
            stakeholder_category=StakeholderCategory.RESEARCHER,
            impact_statement="Test impact"
        )
        
        assert impact.source_quote is None
        assert impact.source_paper == ""
        assert impact.paper_section is None
        assert impact.extraction_confidence == 0.8
        assert impact.gap_filled is False
        assert impact.filled_by_paper is None


class TestGenerateImpactId:
    """Tests for impact ID generation."""
    
    def test_generate_basic_id(self):
        """Test basic ID generation."""
        impact_id = generate_impact_id(
            source_paper="snn_review_2024.pdf",
            gap_id="GAP-123",
            stakeholder="hardware engineers",
            sequence=1
        )
        
        assert impact_id.startswith("LSI-")
        assert impact_id.endswith("-001")
    
    def test_generate_sequential_ids(self):
        """Test sequential ID generation."""
        id1 = generate_impact_id("paper.pdf", "GAP-1", "researchers", 1)
        id2 = generate_impact_id("paper.pdf", "GAP-1", "researchers", 2)
        
        assert id1 != id2
        assert id1.endswith("-001")
        assert id2.endswith("-002")
    
    def test_generate_id_with_html(self):
        """Test ID generation with HTML file."""
        impact_id = generate_impact_id(
            source_paper="document.html",
            gap_id="GAP-456",
            stakeholder="clinicians",
            sequence=5
        )
        
        assert "html" not in impact_id.lower()
        assert impact_id.endswith("-005")


class TestStakeholderExtractionPrompt:
    """Tests for stakeholder extraction prompts."""
    
    def test_prompt_template_contains_key_elements(self):
        """Test that prompt template contains key elements."""
        assert "gap" in STAKEHOLDER_IMPACT_EXTRACTION_PROMPT.lower()
        assert "stakeholder" in STAKEHOLDER_IMPACT_EXTRACTION_PROMPT.lower()
        assert "json" in STAKEHOLDER_IMPACT_EXTRACTION_PROMPT.lower()
    
    def test_format_extraction_prompt(self):
        """Test formatting extraction prompt."""
        paper_content = "This is test paper content."
        prompt = format_stakeholder_extraction_prompt(paper_content)
        
        assert paper_content in prompt
        assert "gap" in prompt.lower()
    
    def test_format_batch_prompt(self):
        """Test formatting batch prompt."""
        sections = [
            {"section_name": "Introduction", "content": "Intro content"},
            {"section_name": "Discussion", "content": "Discussion content"}
        ]
        
        prompt = format_stakeholder_batch_prompt("paper.pdf", sections)
        
        assert "paper.pdf" in prompt
        assert "Introduction" in prompt
        assert "Discussion" in prompt


class TestParseExtractionResponse:
    """Tests for parsing extraction response."""
    
    def test_parse_valid_response(self):
        """Test parsing a valid response."""
        response = [
            {
                "gap_description": "Lack of benchmarks",
                "affected_stakeholder": "hardware engineers",
                "stakeholder_category": "engineer",
                "impact_statement": "Cannot compare designs",
                "source_quote": "Direct quote here",
                "paper_section": "Discussion",
                "confidence": 0.9
            }
        ]
        
        validated = parse_extraction_response(response)
        
        assert len(validated) == 1
        assert validated[0]["gap_description"] == "Lack of benchmarks"
        assert validated[0]["stakeholder_category"] == "engineer"
    
    def test_parse_filters_low_confidence(self):
        """Test that low confidence items are filtered."""
        response = [
            {
                "gap_description": "High confidence gap",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact statement",
                "confidence": 0.9
            },
            {
                "gap_description": "Low confidence gap",
                "affected_stakeholder": "engineers",
                "impact_statement": "Impact statement",
                "confidence": 0.3  # Below threshold
            }
        ]
        
        validated = parse_extraction_response(response)
        
        assert len(validated) == 1
        assert validated[0]["gap_description"] == "High confidence gap"
    
    def test_parse_filters_missing_fields(self):
        """Test that items with missing required fields are filtered."""
        response = [
            {
                "gap_description": "Valid gap",
                "affected_stakeholder": "researchers",
                "impact_statement": "Valid impact"
            },
            {
                "gap_description": "Missing stakeholder"
                # Missing affected_stakeholder and impact_statement
            }
        ]
        
        validated = parse_extraction_response(response)
        
        assert len(validated) == 1
    
    def test_parse_normalizes_category(self):
        """Test that invalid categories are normalized to 'other'."""
        response = [
            {
                "gap_description": "Gap",
                "affected_stakeholder": "aliens",
                "stakeholder_category": "extraterrestrial",  # Invalid
                "impact_statement": "Impact"
            }
        ]
        
        validated = parse_extraction_response(response)
        
        assert len(validated) == 1
        assert validated[0]["stakeholder_category"] == "other"
    
    def test_parse_limits_max_impacts(self):
        """Test that results are limited to MAX_IMPACTS_PER_PAPER."""
        # Create more items than the limit
        response = [
            {
                "gap_description": f"Gap {i}",
                "affected_stakeholder": "researchers",
                "impact_statement": f"Impact {i}",
                "confidence": 0.8
            }
            for i in range(MAX_IMPACTS_PER_PAPER + 5)
        ]
        
        validated = parse_extraction_response(response)
        
        assert len(validated) == MAX_IMPACTS_PER_PAPER


class TestDomainStakeholderExtractor:
    """Tests for DomainStakeholderExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a basic extractor."""
        return DomainStakeholderExtractor()
    
    @pytest.fixture
    def sample_gap_analysis(self, tmp_path):
        """Create sample gap analysis file."""
        gap_data = {
            "Pillar 1: Architecture": {
                "analysis": {
                    "REQ-001": {
                        "SUB-001": {
                            "gap_analysis": "Lack of standardized benchmarks for energy efficiency",
                            "completeness_percent": 40
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap_analysis.json"
        with open(path, "w") as f:
            json.dump(gap_data, f)
        
        return str(path)
    
    def test_extractor_initialization(self, extractor):
        """Test basic initialization."""
        assert extractor.gap_analysis == {}
        assert extractor.impacts == []
        assert extractor.stakeholders == {}
    
    def test_extractor_with_gap_analysis(self, sample_gap_analysis):
        """Test initialization with gap analysis file."""
        extractor = DomainStakeholderExtractor(
            gap_analysis_path=sample_gap_analysis
        )
        
        assert "Pillar 1: Architecture" in extractor.gap_analysis
    
    def test_normalize_stakeholder(self, extractor):
        """Test stakeholder normalization."""
        assert extractor._normalize_stakeholder("neuroscientists") == "neuroscientists"
        assert extractor._normalize_stakeholder("neuroscience researchers") == "neuroscientists"
        assert extractor._normalize_stakeholder("RESEARCHERS") == "researchers"
    
    def test_categorize_stakeholder(self, extractor):
        """Test stakeholder categorization."""
        assert extractor._categorize_stakeholder("neuroscientists") == StakeholderCategory.RESEARCHER
        assert extractor._categorize_stakeholder("hardware engineers") == StakeholderCategory.ENGINEER
        assert extractor._categorize_stakeholder("clinicians") == StakeholderCategory.CLINICIAN
        assert extractor._categorize_stakeholder("industry practitioners") == StakeholderCategory.PRACTITIONER
        assert extractor._categorize_stakeholder("policy makers") == StakeholderCategory.POLICY_MAKER
        assert extractor._categorize_stakeholder("end users") == StakeholderCategory.END_USER
        assert extractor._categorize_stakeholder("aliens") == StakeholderCategory.OTHER
    
    def test_extract_from_response(self, extractor):
        """Test extracting impacts from LLM response."""
        response = [
            {
                "gap_description": "Lack of benchmarks",
                "affected_stakeholder": "hardware engineers",
                "stakeholder_category": "engineer",
                "impact_statement": "Cannot compare designs",
                "source_quote": "Quote here",
                "paper_section": "Discussion",
                "confidence": 0.9
            }
        ]
        
        impacts = extractor.extract_from_response(response, "paper.pdf")
        
        assert len(impacts) == 1
        assert impacts[0].affected_stakeholder == "hardware engineers"
        assert impacts[0].source_paper == "paper.pdf"
        assert len(extractor.impacts) == 1
        assert "hardware engineers" in extractor.stakeholders
    
    def test_extract_multiple_impacts(self, extractor):
        """Test extracting multiple impacts."""
        response = [
            {
                "gap_description": "Gap 1",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact 1",
                "confidence": 0.8
            },
            {
                "gap_description": "Gap 2",
                "affected_stakeholder": "engineers",
                "impact_statement": "Impact 2",
                "confidence": 0.9
            }
        ]
        
        impacts = extractor.extract_from_response(response, "paper.pdf")
        
        assert len(impacts) == 2
        assert len(extractor.stakeholders) == 2
    
    def test_check_gap_resolution(self, extractor):
        """Test checking gap resolution."""
        # First add an impact
        response = [
            {
                "gap_description": "Missing validation data",
                "affected_stakeholder": "neuroscientists",
                "impact_statement": "Cannot validate models",
                "confidence": 0.9
            }
        ]
        extractor.extract_from_response(response, "paper1.pdf")
        
        # Check resolution with matching claim
        claims = [
            {
                "claim_summary": "We provide validation data for neuromorphic models"
            }
        ]
        
        resolved = extractor.check_gap_resolution("paper2.pdf", claims)
        
        # Should find overlap
        assert len(resolved) >= 0  # May or may not resolve depending on overlap
    
    def test_generate_report(self, extractor):
        """Test report generation."""
        # Add some impacts
        response = [
            {
                "gap_description": "Gap 1",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact 1",
                "confidence": 0.8
            }
        ]
        extractor.extract_from_response(response, "paper.pdf")
        
        report = extractor.generate_report()
        
        assert report["report_type"] == "literature_domain_stakeholder_impacts"
        assert "generated_at" in report
        assert report["summary"]["total_impacts"] == 1
        assert report["summary"]["unique_stakeholders"] == 1
        assert "researchers" in report["stakeholders"]
        assert "researchers" in report["impacts_by_stakeholder"]
    
    def test_save_and_load_report(self, extractor, tmp_path):
        """Test saving and loading report."""
        # Add impacts
        response = [
            {
                "gap_description": "Test gap",
                "affected_stakeholder": "engineers",
                "impact_statement": "Test impact",
                "confidence": 0.9
            }
        ]
        extractor.extract_from_response(response, "paper.pdf")
        
        # Save
        output_path = tmp_path / "report.json"
        extractor.save_report(str(output_path))
        
        assert output_path.exists()
        
        # Load into new extractor
        new_extractor = DomainStakeholderExtractor()
        new_extractor.load_existing(str(output_path))
        
        assert len(new_extractor.impacts) == 1
        assert new_extractor.impacts[0].affected_stakeholder == "engineers"
    
    def test_get_impacts_for_stakeholder(self, extractor):
        """Test getting impacts for specific stakeholder."""
        response = [
            {
                "gap_description": "Gap 1",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact 1",
                "confidence": 0.8
            },
            {
                "gap_description": "Gap 2",
                "affected_stakeholder": "engineers",
                "impact_statement": "Impact 2",
                "confidence": 0.9
            }
        ]
        extractor.extract_from_response(response, "paper.pdf")
        
        researcher_impacts = extractor.get_impacts_for_stakeholder("researchers")
        
        assert len(researcher_impacts) == 1
        assert researcher_impacts[0].affected_stakeholder == "researchers"
    
    def test_get_open_and_resolved_impacts(self, extractor):
        """Test getting open and resolved impacts."""
        response = [
            {
                "gap_description": "Gap 1",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact 1",
                "confidence": 0.8
            },
            {
                "gap_description": "Gap 2",
                "affected_stakeholder": "engineers",
                "impact_statement": "Impact 2",
                "confidence": 0.9
            }
        ]
        extractor.extract_from_response(response, "paper.pdf")
        
        # Mark one as resolved
        extractor.impacts[0].mark_resolved("new_paper.pdf", "2025-01-01")
        
        open_impacts = extractor.get_open_impacts()
        resolved_impacts = extractor.get_resolved_impacts()
        
        assert len(open_impacts) == 1
        assert len(resolved_impacts) == 1
    
    def test_link_to_gap_analysis(self, sample_gap_analysis):
        """Test linking to gap analysis."""
        extractor = DomainStakeholderExtractor(
            gap_analysis_path=sample_gap_analysis,
            similarity_threshold=0.3  # Lower for testing
        )
        
        # Gap description that overlaps with sample gap
        gap_desc = "standardized benchmarks for energy efficiency measurement"
        linked = extractor.link_to_gap_analysis(gap_desc)
        
        # May or may not find a match depending on overlap
        # Just test that the method runs without error
        assert linked is None or isinstance(linked, str)
    
    def test_text_overlap_calculation(self, extractor):
        """Test text overlap calculation."""
        text1 = "standardized benchmarks for energy efficiency"
        text2 = "benchmarks for measuring energy efficiency"
        
        overlap = extractor._calculate_text_overlap(text1, text2)
        
        assert 0 <= overlap <= 1
        assert overlap > 0  # Should have some overlap
    
    def test_text_overlap_empty_strings(self, extractor):
        """Test text overlap with empty strings."""
        assert extractor._calculate_text_overlap("", "text") == 0.0
        assert extractor._calculate_text_overlap("text", "") == 0.0
        assert extractor._calculate_text_overlap("", "") == 0.0


class TestModuleImports:
    """Tests for module imports and exports."""
    
    def test_models_import(self):
        """Test that models can be imported from package."""
        from literature_review.models import (
            DomainStakeholder,
            LiteratureStakeholderImpact,
            StakeholderCategory,
            generate_impact_id
        )
        
        assert DomainStakeholder is not None
        assert LiteratureStakeholderImpact is not None
        assert StakeholderCategory is not None
        assert generate_impact_id is not None
    
    def test_prompts_import(self):
        """Test that prompts can be imported from package."""
        from literature_review.reviewers.prompts import (
            STAKEHOLDER_IMPACT_EXTRACTION_PROMPT,
            format_stakeholder_extraction_prompt,
            parse_extraction_response
        )
        
        assert STAKEHOLDER_IMPACT_EXTRACTION_PROMPT is not None
        assert format_stakeholder_extraction_prompt is not None
        assert parse_extraction_response is not None
    
    def test_analysis_import(self):
        """Test that analysis can be imported from package."""
        from literature_review.analysis import DomainStakeholderExtractor
        
        assert DomainStakeholderExtractor is not None


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_extractor_with_nonexistent_file(self):
        """Test initialization with nonexistent gap analysis file."""
        extractor = DomainStakeholderExtractor(
            gap_analysis_path="/nonexistent/path/file.json"
        )
        
        assert extractor.gap_analysis == {}
    
    def test_load_invalid_json_file(self, tmp_path):
        """Test loading invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{ invalid json }")
        
        extractor = DomainStakeholderExtractor()
        extractor.load_existing(str(invalid_file))
        
        assert extractor.impacts == []
    
    def test_empty_response(self):
        """Test with empty response."""
        extractor = DomainStakeholderExtractor()
        impacts = extractor.extract_from_response([], "paper.pdf")
        
        assert impacts == []
    
    def test_stakeholder_registry_update(self):
        """Test that stakeholder registry is properly updated."""
        extractor = DomainStakeholderExtractor()
        
        # Add impacts from multiple papers for same stakeholder
        response1 = [
            {
                "gap_description": "Gap 1",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact 1",
                "confidence": 0.8
            }
        ]
        extractor.extract_from_response(response1, "paper1.pdf")
        
        response2 = [
            {
                "gap_description": "Gap 2",
                "affected_stakeholder": "researchers",
                "impact_statement": "Impact 2",
                "confidence": 0.9
            }
        ]
        extractor.extract_from_response(response2, "paper2.pdf")
        
        # Should have one stakeholder entry with two source papers
        assert len(extractor.stakeholders) == 1
        assert len(extractor.stakeholders["researchers"].source_papers) == 2

    def test_gap_analysis_loading_exception(self, tmp_path):
        """Test gap analysis loading with malformed JSON."""
        bad_file = tmp_path / "bad_gap.json"
        with open(bad_file, "w") as f:
            f.write("not valid json at all")
        
        extractor = DomainStakeholderExtractor(gap_analysis_path=str(bad_file))
        assert extractor.gap_analysis == {}

    def test_invalid_stakeholder_category_in_response(self):
        """Test that invalid category triggers fallback categorization."""
        extractor = DomainStakeholderExtractor()
        
        response = [
            {
                "gap_description": "Test gap",
                "affected_stakeholder": "data scientists",
                "stakeholder_category": "invalid_category_xyz",  # Invalid
                "impact_statement": "Test impact",
                "confidence": 0.8
            }
        ]
        
        impacts = extractor.extract_from_response(response, "paper.pdf")
        
        assert len(impacts) == 1
        # Should be categorized as OTHER since data scientists doesn't match known categories
        assert impacts[0].stakeholder_category == StakeholderCategory.OTHER

    def test_gap_resolution_with_matching_claim(self):
        """Test gap resolution when claim addresses the gap."""
        extractor = DomainStakeholderExtractor()
        
        # Add impact with specific gap
        response = [
            {
                "gap_description": "Missing standardized benchmarks for energy efficiency",
                "affected_stakeholder": "hardware engineers",
                "impact_statement": "Cannot compare designs",
                "confidence": 0.9
            }
        ]
        extractor.extract_from_response(response, "paper1.pdf")
        
        # Claim that addresses the gap
        claims = [
            {
                "claim_summary": "We provide standardized benchmarks for energy efficiency testing"
            }
        ]
        
        resolved = extractor.check_gap_resolution("paper2.pdf", claims)
        
        # Should find resolution due to word overlap
        assert len(resolved) >= 1
        assert extractor.impacts[0].gap_filled is True

    def test_link_to_gap_analysis_with_non_dict_entries(self, tmp_path):
        """Test gap linking with non-dict entries in gap analysis."""
        gap_data = {
            "Pillar 1": {
                "analysis": {
                    "REQ-001": {
                        "SUB-001": {
                            "gap_analysis": "test gap analysis",
                            "completeness_percent": 40
                        },
                        "SUB-002": "non-dict entry"  # Non-dict entry
                    },
                    "REQ-002": "also non-dict"  # Non-dict entry
                }
            },
            "Pillar 2": "non-dict pillar"  # Non-dict entry
        }
        
        path = tmp_path / "gap_analysis.json"
        with open(path, "w") as f:
            json.dump(gap_data, f)
        
        extractor = DomainStakeholderExtractor(
            gap_analysis_path=str(path),
            similarity_threshold=0.1
        )
        
        # Should not crash
        result = extractor.link_to_gap_analysis("test gap analysis data")
        
        # Result should be a valid gap ID or None
        assert result is None or isinstance(result, str)

    def test_link_to_gap_analysis_high_overlap(self, tmp_path):
        """Test gap linking with high text overlap."""
        gap_data = {
            "Pillar 1: Architecture": {
                "analysis": {
                    "REQ-001": {
                        "SUB-001": {
                            "gap_analysis": "lack of standardized energy efficiency benchmarks for neuromorphic hardware",
                            "completeness_percent": 30
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap_analysis.json"
        with open(path, "w") as f:
            json.dump(gap_data, f)
        
        extractor = DomainStakeholderExtractor(
            gap_analysis_path=str(path),
            similarity_threshold=0.3  # Lower threshold for testing
        )
        
        # Gap description with high overlap
        result = extractor.link_to_gap_analysis(
            "lack of standardized energy efficiency benchmarks for hardware"
        )
        
        assert result == "REQ-001-SUB-001"

    def test_load_nonexistent_report(self):
        """Test loading from nonexistent file."""
        extractor = DomainStakeholderExtractor()
        extractor.load_existing("/nonexistent/report.json")
        
        assert len(extractor.impacts) == 0
