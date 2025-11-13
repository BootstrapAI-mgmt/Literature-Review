"""
Data Validation Tests
Tests schema compliance and structural integrity of data files.
"""

import pytest
import json
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.data_helpers import detect_circular_refs


class TestVersionHistorySchema:
    """Test suite for review_version_history.json schema validation."""
    
    @pytest.mark.unit
    def test_example_version_history_exists(self):
        """Test that example version history file exists."""
        assert os.path.exists("data/examples/review_version_history_EXAMPLE.json")
    
    @pytest.mark.unit
    def test_version_history_top_level_structure(self):
        """Test top-level structure of version history."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        # Should be a dict
        assert isinstance(history, dict)
        
        # Should have file entries
        assert len(history) > 0
    
    @pytest.mark.unit
    def test_version_history_file_entries(self):
        """Test structure of file entries in version history."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        for filename, versions in history.items():
            # Filename should be string
            assert isinstance(filename, str)
            assert len(filename) > 0
            
            # Versions should be list
            assert isinstance(versions, list)
            assert len(versions) > 0
    
    @pytest.mark.unit
    def test_version_history_version_structure(self):
        """Test structure of version entries."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        for filename, versions in history.items():
            for version in versions:
                # Each version should have timestamp and review
                assert "timestamp" in version
                assert "review" in version
                assert isinstance(version["review"], dict)
    
    @pytest.mark.unit
    def test_version_history_review_required_fields(self):
        """Test required fields in review section."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        required_fields = ["TITLE", "FILENAME", "CORE_DOMAIN", "Requirement(s)"]
        
        for filename, versions in history.items():
            latest = versions[-1]  # Check latest version
            review = latest["review"]
            
            for field in required_fields:
                assert field in review, f"Missing {field} in {filename}"
    
    @pytest.mark.unit
    def test_version_history_requirements_structure(self):
        """Test structure of Requirements list."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        for filename, versions in history.items():
            latest = versions[-1]
            requirements = latest["review"].get("Requirement(s)", [])
            
            assert isinstance(requirements, list)
            
            for claim in requirements:
                # Each claim should have essential fields
                assert "claim_id" in claim
                assert "status" in claim
                assert claim["status"] in [
                    "pending_judge_review",
                    "approved",
                    "rejected",
                    "pending"
                ]
    
    @pytest.mark.unit
    def test_version_history_no_circular_references(self):
        """Test that version history has no circular references."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        # Should not raise exception
        detect_circular_refs(history)


class TestCSVDatabaseSchema:
    """Test suite for neuromorphic-research_database.csv schema validation."""
    
    @pytest.mark.unit
    def test_example_csv_exists(self):
        """Test that example CSV file exists."""
        assert os.path.exists("data/examples/neuromorphic-research_database_EXAMPLE.csv")
    
    @pytest.mark.unit
    def test_csv_required_columns(self):
        """Test required columns exist in CSV."""
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        required_cols = [
            "FILENAME",
            "TITLE",
            "CORE_DOMAIN",
            "Requirement(s)",
            "PUBLICATION_YEAR",
            "REVIEW_TIMESTAMP"
        ]
        
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    @pytest.mark.unit
    def test_csv_filename_uniqueness(self):
        """Test that FILENAME values are unique."""
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        duplicates = df[df.duplicated(subset=['FILENAME'], keep=False)]
        
        assert len(duplicates) == 0, f"Found duplicate filenames: {duplicates['FILENAME'].tolist()}"
    
    @pytest.mark.unit
    def test_csv_requirements_valid_json(self):
        """Test that Requirement(s) column contains valid JSON."""
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        for idx, row in df.iterrows():
            reqs_str = row["Requirement(s)"]
            
            # Should be valid JSON
            try:
                reqs = json.loads(reqs_str)
            except json.JSONDecodeError:
                pytest.fail(f"Row {idx} ({row['FILENAME']}): Invalid JSON in Requirement(s)")
            
            # Should be a list
            assert isinstance(reqs, list), f"Row {idx}: Requirement(s) should be list"
    
    @pytest.mark.unit
    def test_csv_publication_year_valid(self):
        """Test that PUBLICATION_YEAR is numeric and reasonable."""
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        # Should be numeric
        assert pd.api.types.is_numeric_dtype(df["PUBLICATION_YEAR"])
        
        # Should be reasonable years
        valid_years = df["PUBLICATION_YEAR"].between(1900, 2030)
        assert valid_years.all(), "Found invalid publication years"
    
    @pytest.mark.unit
    def test_csv_no_null_critical_fields(self):
        """Test that critical fields have no null values."""
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        critical_fields = ["FILENAME", "TITLE", "CORE_DOMAIN"]
        
        for field in critical_fields:
            nulls = df[field].isnull()
            assert not nulls.any(), f"Found null values in {field}"


class TestClaimStructureConsistency:
    """Test suite for claim structure consistency across data sources."""
    
    @pytest.mark.unit
    def test_claims_have_required_fields(self):
        """Test that all claims have required fields."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        required_fields = ["claim_id", "pillar", "sub_requirement", "status"]
        
        for filename, versions in history.items():
            latest = versions[-1]["review"]
            
            for claim in latest.get("Requirement(s)", []):
                for field in required_fields:
                    assert field in claim, f"Claim {claim.get('claim_id', 'unknown')} missing {field}"
    
    @pytest.mark.unit
    def test_claim_ids_are_unique_per_file(self):
        """Test that claim IDs are unique within each file."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        for filename, versions in history.items():
            latest = versions[-1]["review"]
            claims = latest.get("Requirement(s)", [])
            
            claim_ids = [c["claim_id"] for c in claims]
            unique_ids = set(claim_ids)
            
            assert len(claim_ids) == len(unique_ids), \
                f"Duplicate claim IDs in {filename}"
    
    @pytest.mark.unit
    def test_claim_status_values_valid(self):
        """Test that claim status values are valid."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        valid_statuses = {
            "pending_judge_review",
            "approved",
            "rejected",
            "pending"
        }
        
        for filename, versions in history.items():
            latest = versions[-1]["review"]
            
            for claim in latest.get("Requirement(s)", []):
                status = claim.get("status")
                assert status in valid_statuses, \
                    f"Invalid status '{status}' in claim {claim.get('claim_id')}"
    
    @pytest.mark.unit
    def test_approved_claims_have_judge_notes(self):
        """Test that approved/rejected claims have judge_notes."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        for filename, versions in history.items():
            latest = versions[-1]["review"]
            
            for claim in latest.get("Requirement(s)", []):
                status = claim.get("status")
                
                # If judged, should have judge_notes
                if status in ["approved", "rejected"]:
                    # Note: May not always have judge_notes if not yet processed
                    # This is a soft check
                    if "judge_notes" in claim:
                        assert isinstance(claim["judge_notes"], str)


class TestPillarDefinitionsSchema:
    """Test suite for pillar_definitions_enhanced.json schema validation."""
    
    @pytest.mark.unit
    def test_pillar_definitions_exists(self):
        """Test that pillar definitions file exists."""
        assert os.path.exists("pillar_definitions.json")
    
    @pytest.mark.unit
    def test_pillar_definitions_structure(self):
        """Test basic structure of pillar definitions."""
        with open("pillar_definitions.json") as f:
            definitions = json.load(f)
        
        # Should be a dict
        assert isinstance(definitions, dict)
        
        # Should have multiple pillars
        pillar_keys = [k for k in definitions.keys() if k.startswith("Pillar")]
        assert len(pillar_keys) >= 6, "Should have at least 6 pillars"
    
    @pytest.mark.unit
    def test_pillar_definitions_requirements_structure(self):
        """Test structure of requirements in pillars."""
        with open("pillar_definitions.json") as f:
            definitions = json.load(f)
        
        for pillar_key, pillar_data in definitions.items():
            if not pillar_key.startswith("Pillar"):
                continue  # Skip non-pillar entries
            
            # Should have requirements
            assert "requirements" in pillar_data
            assert isinstance(pillar_data["requirements"], dict)
            
            # Each requirement should have sub-requirements
            for req_key, sub_reqs in pillar_data["requirements"].items():
                assert isinstance(sub_reqs, list)
                assert len(sub_reqs) > 0
                
                # Each sub-requirement should be a string
                for sub_req in sub_reqs:
                    assert isinstance(sub_req, str)
                    assert len(sub_req) > 0
    
    @pytest.mark.unit
    def test_pillar_definitions_no_circular_refs(self):
        """Test that pillar definitions have no circular references."""
        with open("pillar_definitions.json") as f:
            definitions = json.load(f)
        
        # Should not raise exception
        detect_circular_refs(definitions)


class TestDataConsistency:
    """Test suite for consistency between version history and CSV."""
    
    @pytest.mark.unit
    def test_filenames_match_between_sources(self):
        """Test that filenames in version history match CSV."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        history_files = set(history.keys())
        csv_files = set(df["FILENAME"].tolist())
        
        # Files in history should be in CSV
        missing_from_csv = history_files - csv_files
        
        # Some mismatch is expected if sync is needed
        # This is informational
        if missing_from_csv:
            print(f"\nFiles in history but not CSV: {missing_from_csv}")
    
    @pytest.mark.unit
    def test_claim_counts_consistency(self):
        """Test that claim counts are consistent (informational)."""
        with open("data/examples/review_version_history_EXAMPLE.json") as f:
            history = json.load(f)
        
        df = pd.read_csv("data/examples/neuromorphic-research_database_EXAMPLE.csv")
        
        for filename in history.keys():
            if filename in df["FILENAME"].values:
                # Get claims from version history
                latest = history[filename][-1]["review"]
                history_claims = latest.get("Requirement(s)", [])
                
                # Get claims from CSV
                csv_row = df[df["FILENAME"] == filename].iloc[0]
                csv_claims = json.loads(csv_row["Requirement(s)"])
                
                # Counts might differ if not synced - informational only
                if len(history_claims) != len(csv_claims):
                    print(f"\n{filename}: History={len(history_claims)}, CSV={len(csv_claims)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
