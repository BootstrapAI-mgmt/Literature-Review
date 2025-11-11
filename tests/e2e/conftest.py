"""
Pytest configuration for end-to-end tests.

E2E tests run the full pipeline with realistic test data.
"""

import pytest
import os
import sys

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


@pytest.fixture(scope="function")
def e2e_workspace(temp_dir):
    """
    Create a complete workspace for E2E tests.
    
    Args:
        temp_dir: Temporary directory from parent conftest
        
    Returns:
        Dict with paths to all required files
    """
    workspace = {
        'root': temp_dir,
        'version_history': os.path.join(temp_dir, 'review_version_history.json'),
        'csv_db': os.path.join(temp_dir, 'neuromorphic-research_database.csv'),
        'non_journal_db': os.path.join(temp_dir, 'non-journal_database.csv'),
        'pillar_definitions': os.path.join(temp_dir, 'pillar_definitions_enhanced.json'),
        'papers_dir': os.path.join(temp_dir, 'Research-Papers'),
        'reports_dir': os.path.join(temp_dir, 'reports'),
        'logs_dir': os.path.join(temp_dir, 'logs')
    }
    
    # Create all directories
    for key in ['papers_dir', 'reports_dir', 'logs_dir']:
        os.makedirs(workspace[key], exist_ok=True)
    
    return workspace


@pytest.fixture(scope="function")
def e2e_sample_papers(e2e_workspace, sample_paper_filenames):
    """
    Create sample paper files for E2E testing.
    
    Args:
        e2e_workspace: E2E workspace fixture
        sample_paper_filenames: List of filenames
        
    Returns:
        List of paths to created sample papers
    """
    papers = []
    
    for filename in sample_paper_filenames[:3]:  # Use first 3 for E2E
        filepath = os.path.join(e2e_workspace['papers_dir'], filename)
        
        # Create a minimal mock PDF (just for testing file existence)
        with open(filepath, 'wb') as f:
            f.write(b'%PDF-1.4\nMock PDF content for testing\n%%EOF')
        
        papers.append(filepath)
    
    return papers
