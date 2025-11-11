"""
Sample E2E test to verify infrastructure works.

This is a minimal test to validate the E2E test infrastructure.
Will be replaced by actual E2E tests in subsequent task cards.
"""

import pytest
import os


class TestE2EInfrastructure:
    """Verify that E2E test infrastructure is working."""
    
    @pytest.mark.e2e
    def test_e2e_workspace_fixture(self, e2e_workspace):
        """Test that E2E workspace fixture works."""
        workspace = e2e_workspace
        
        # Verify all expected keys exist
        assert 'root' in workspace
        assert 'version_history' in workspace
        assert 'csv_db' in workspace
        assert 'pillar_definitions' in workspace
        assert 'papers_dir' in workspace
        assert 'reports_dir' in workspace
        assert 'logs_dir' in workspace
        
        # Verify directories were created
        assert os.path.exists(workspace['papers_dir'])
        assert os.path.exists(workspace['reports_dir'])
        assert os.path.exists(workspace['logs_dir'])
    
    @pytest.mark.e2e
    def test_sample_papers_fixture(self, e2e_sample_papers, e2e_workspace):
        """Test that sample papers fixture creates files."""
        papers = e2e_sample_papers
        
        # Verify papers were created
        assert len(papers) > 0
        
        for paper_path in papers:
            assert os.path.exists(paper_path)
            
            # Verify it's in the workspace papers directory
            assert os.path.dirname(paper_path) == e2e_workspace['papers_dir']
            
            # Verify file has content
            assert os.path.getsize(paper_path) > 0
