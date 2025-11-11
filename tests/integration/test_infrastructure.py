"""
Sample integration test to verify infrastructure works.

This is a minimal test to validate the integration test infrastructure.
Will be replaced by actual integration tests in subsequent task cards.
"""

import pytest
import os
import json


class TestInfrastructure:
    """Verify that test infrastructure is working."""
    
    @pytest.mark.integration
    def test_fixtures_available(self, temp_dir, test_data_generator):
        """Test that shared fixtures are available."""
        assert os.path.exists(temp_dir)
        assert test_data_generator is not None
    
    @pytest.mark.integration
    def test_mock_version_history_fixture(self, mock_version_history):
        """Test that mock version history fixture works."""
        filepath, data = mock_version_history
        
        # Verify file was created
        assert os.path.exists(filepath)
        
        # Verify data structure
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify content
        for filename, versions in data.items():
            assert isinstance(versions, list)
            assert len(versions) > 0
            
            latest = versions[-1]
            assert 'version' in latest
            assert 'timestamp' in latest
            assert 'review' in latest
    
    @pytest.mark.integration
    def test_integration_workspace_fixture(self, integration_temp_workspace):
        """Test that integration workspace fixture works."""
        workspace = integration_temp_workspace
        
        # Verify all expected keys exist
        assert 'root' in workspace
        assert 'version_history' in workspace
        assert 'csv_db' in workspace
        assert 'pillar_definitions' in workspace
        assert 'papers_dir' in workspace
        
        # Verify papers directory was created
        assert os.path.exists(workspace['papers_dir'])
    
    @pytest.mark.integration
    def test_data_generator_creates_realistic_data(self, test_data_generator, temp_dir):
        """Test that data generator creates realistic test data."""
        # Create version history
        history = test_data_generator.create_version_history(
            filenames=["test1.pdf", "test2.pdf"],
            num_versions_per_file=2,
            approved_ratio=0.7
        )
        
        assert len(history) == 2
        
        for filename, versions in history.items():
            assert len(versions) == 2
            
            # Check version numbers
            assert versions[0]['version'] == 1
            assert versions[1]['version'] == 2
            
            # Check claims exist
            for version in versions:
                claims = version['review']['Requirement(s)']
                assert len(claims) > 0
                
                # Check claim structure
                for claim in claims:
                    assert 'pillar' in claim
                    assert 'claim' in claim
                    assert 'evidence' in claim
                    assert 'status' in claim
