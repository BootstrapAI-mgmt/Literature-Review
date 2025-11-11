"""
Pytest configuration for integration tests.

Integration tests verify interactions between multiple components.
"""

import pytest
import os
import sys

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


@pytest.fixture(scope="function")
def integration_temp_workspace(temp_dir):
    """
    Create a workspace for integration tests with typical file structure.
    
    Args:
        temp_dir: Temporary directory from parent conftest
        
    Returns:
        Dict with paths to common files
    """
    workspace = {
        'root': temp_dir,
        'version_history': os.path.join(temp_dir, 'review_version_history.json'),
        'csv_db': os.path.join(temp_dir, 'neuromorphic-research_database.csv'),
        'pillar_definitions': os.path.join(temp_dir, 'pillar_definitions_enhanced.json'),
        'papers_dir': os.path.join(temp_dir, 'Research-Papers')
    }
    
    # Create papers directory
    os.makedirs(workspace['papers_dir'], exist_ok=True)
    
    return workspace


@pytest.fixture(scope="function")
def mock_journal_output(integration_temp_workspace, test_data_generator):
    """
    Create mock output from Journal-Reviewer.
    
    Args:
        integration_temp_workspace: Workspace fixture
        test_data_generator: Test data generator
        
    Returns:
        Path to version history with initial reviews
    """
    import json
    
    data = test_data_generator.create_version_history(
        filenames=["paper1.pdf", "paper2.pdf"],
        num_versions_per_file=1,
        approved_ratio=1.0  # All pending initially
    )
    
    filepath = integration_temp_workspace['version_history']
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath
