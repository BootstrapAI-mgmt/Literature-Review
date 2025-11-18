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


# Dashboard E2E test fixtures
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context for dashboard E2E tests.
    Allows API key header to be set for authenticated requests.
    """
    return {
        **browser_context_args,
        "ignore_https_errors": True,
        "viewport": {"width": 1920, "height": 1080}
    }


@pytest.fixture(scope="function")
def dashboard_test_pdf(tmp_path):
    """
    Create a minimal test PDF file for dashboard upload tests.
    
    Returns:
        Path to the created PDF file
    """
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000265 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
357
%%EOF
"""
    
    pdf_path = tmp_path / "test_dashboard_paper.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path
