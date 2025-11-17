"""
Unit tests for duplicate detection functionality
"""

import tempfile
from pathlib import Path

import pytest

from webdashboard.duplicate_detector import (
    compute_pdf_hash,
    check_for_duplicates,
    load_existing_papers_from_review_log
)


def create_test_pdf(content: bytes = b"Test PDF content") -> Path:
    """Create a temporary PDF file with given content"""
    # Create minimal valid PDF
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
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
178
%%EOF
""" + content
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.write(pdf_content)
    temp_file.close()
    return Path(temp_file.name)


class TestComputePdfHash:
    """Tests for PDF hash computation"""
    
    def test_hash_consistency(self):
        """Test that same content produces same hash"""
        pdf1 = create_test_pdf(b"Same content")
        pdf2 = create_test_pdf(b"Same content")
        
        try:
            hash1 = compute_pdf_hash(pdf1)
            hash2 = compute_pdf_hash(pdf2)
            
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 produces 64 hex characters
        finally:
            pdf1.unlink()
            pdf2.unlink()
    
    def test_hash_difference(self):
        """Test that different content produces different hash"""
        pdf1 = create_test_pdf(b"Content A")
        pdf2 = create_test_pdf(b"Content B")
        
        try:
            hash1 = compute_pdf_hash(pdf1)
            hash2 = compute_pdf_hash(pdf2)
            
            assert hash1 != hash2
        finally:
            pdf1.unlink()
            pdf2.unlink()
    
    def test_hash_format(self):
        """Test that hash is valid hexadecimal string"""
        pdf = create_test_pdf()
        
        try:
            hash_value = compute_pdf_hash(pdf)
            
            # Should be valid hex
            int(hash_value, 16)
            assert len(hash_value) == 64
        finally:
            pdf.unlink()


class TestCheckForDuplicates:
    """Tests for duplicate detection logic"""
    
    def test_hash_based_duplicate_detection(self):
        """Test PDF hash duplicate detection"""
        pdf1 = create_test_pdf(b"Identical content")
        pdf2 = create_test_pdf(b"Identical content")
        
        try:
            hash1 = compute_pdf_hash(pdf1)
            
            new_papers = [{
                'title': 'Test Paper',
                'file_path': str(pdf2),
                'original_name': 'paper2.pdf'
            }]
            existing = [{
                'title': 'Test Paper',
                'hash': hash1,
                'id': 'existing1'
            }]
            
            result = check_for_duplicates(new_papers, existing)
            
            assert len(result['duplicates']) == 1
            assert len(result['new']) == 0
            assert result['duplicates'][0]['match_info']['method'] == 'hash'
            assert result['duplicates'][0]['match_info']['confidence'] == 1.0
        finally:
            pdf1.unlink()
            pdf2.unlink()
    
    def test_title_exact_match(self):
        """Test exact title matching"""
        new_papers = [{
            'title': 'Machine Learning Survey',
            'original_name': 'new1.pdf'
        }]
        existing = [{
            'title': 'Machine Learning Survey',
            'id': 'existing1'
        }]
        
        result = check_for_duplicates(new_papers, existing)
        
        assert len(result['duplicates']) == 1
        assert len(result['new']) == 0
        assert result['duplicates'][0]['match_info']['method'] == 'exact_title'
    
    def test_title_case_insensitive(self):
        """Test that title matching is case-insensitive"""
        new_papers = [{
            'title': 'MACHINE LEARNING SURVEY',
            'original_name': 'new1.pdf'
        }]
        existing = [{
            'title': 'machine learning survey',
            'id': 'existing1'
        }]
        
        result = check_for_duplicates(new_papers, existing)
        
        assert len(result['duplicates']) == 1
    
    def test_fuzzy_title_match(self):
        """Test fuzzy title matching (95% threshold)"""
        new_papers = [{
            'title': 'A Survey of Machine Learning Techniques',
            'original_name': 'new1.pdf'
        }]
        existing = [{
            'title': 'Survey of Machine Learning Techniques',
            'id': 'existing1'
        }]
        
        result = check_for_duplicates(new_papers, existing, fuzzy_threshold=0.95)
        
        assert len(result['duplicates']) == 1
        assert result['duplicates'][0]['match_info']['method'] == 'fuzzy_title'
        assert result['duplicates'][0]['match_info']['confidence'] >= 0.95
    
    def test_fuzzy_threshold_respected(self):
        """Test that fuzzy matching respects threshold"""
        new_papers = [{
            'title': 'Machine Learning',
            'original_name': 'new1.pdf'
        }]
        existing = [{
            'title': 'Deep Learning and Neural Networks',
            'id': 'existing1'
        }]
        
        # These titles are not similar enough
        result = check_for_duplicates(new_papers, existing, fuzzy_threshold=0.95)
        
        assert len(result['duplicates']) == 0
        assert len(result['new']) == 1
    
    def test_no_duplicates(self):
        """Test when no duplicates exist"""
        new_papers = [{
            'title': 'New Paper Title',
            'original_name': 'new1.pdf'
        }]
        existing = [{
            'title': 'Existing Paper Title',
            'id': 'existing1'
        }]
        
        result = check_for_duplicates(new_papers, existing)
        
        assert len(result['duplicates']) == 0
        assert len(result['new']) == 1
    
    def test_mixed_duplicates_and_new(self):
        """Test batch with both duplicates and new papers"""
        new_papers = [
            {'title': 'Duplicate Paper', 'original_name': 'dup1.pdf'},
            {'title': 'New Paper', 'original_name': 'new1.pdf'},
            {'title': 'Another Duplicate', 'original_name': 'dup2.pdf'}
        ]
        existing = [
            {'title': 'Duplicate Paper', 'id': 'existing1'},
            {'title': 'Another Duplicate', 'id': 'existing2'},
            {'title': 'Some Other Paper', 'id': 'existing3'}
        ]
        
        result = check_for_duplicates(new_papers, existing)
        
        assert len(result['duplicates']) == 2
        assert len(result['new']) == 1
        assert result['new'][0]['title'] == 'New Paper'
    
    def test_empty_new_papers(self):
        """Test with empty new papers list"""
        result = check_for_duplicates([], [{'title': 'Existing', 'id': '1'}])
        
        assert len(result['duplicates']) == 0
        assert len(result['new']) == 0
        assert len(result['matches']) == 0
    
    def test_empty_existing_database(self):
        """Test with empty existing database"""
        new_papers = [{'title': 'New Paper', 'original_name': 'new1.pdf'}]
        result = check_for_duplicates(new_papers, [])
        
        assert len(result['duplicates']) == 0
        assert len(result['new']) == 1
    
    def test_hash_takes_priority_over_title(self):
        """Test that hash matching takes priority over title matching"""
        pdf1 = create_test_pdf(b"Content A")
        pdf2 = create_test_pdf(b"Content A")
        
        try:
            hash1 = compute_pdf_hash(pdf1)
            
            new_papers = [{
                'title': 'Different Title',  # Different title
                'file_path': str(pdf2),
                'original_name': 'new.pdf'
            }]
            existing = [{
                'title': 'Original Title',
                'hash': hash1,
                'id': 'existing1'
            }]
            
            result = check_for_duplicates(new_papers, existing)
            
            # Should match by hash despite different titles
            assert len(result['duplicates']) == 1
            assert result['duplicates'][0]['match_info']['method'] == 'hash'
        finally:
            pdf1.unlink()
            pdf2.unlink()


class TestLoadExistingPapersFromReviewLog:
    """Tests for loading papers from review_log.json"""
    
    def test_load_list_format(self):
        """Test loading review_log with list format"""
        import json
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        data = [
            {'title': 'Paper 1', 'id': '1'},
            {'title': 'Paper 2', 'id': '2'}
        ]
        json.dump(data, temp_file)
        temp_file.close()
        
        try:
            result = load_existing_papers_from_review_log(Path(temp_file.name))
            assert len(result) == 2
            assert result[0]['title'] == 'Paper 1'
        finally:
            Path(temp_file.name).unlink()
    
    def test_load_dict_format(self):
        """Test loading review_log with dict format"""
        import json
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        data = {
            'papers': [
                {'title': 'Paper 1', 'id': '1'},
                {'title': 'Paper 2', 'id': '2'}
            ]
        }
        json.dump(data, temp_file)
        temp_file.close()
        
        try:
            result = load_existing_papers_from_review_log(Path(temp_file.name))
            assert len(result) == 2
            assert result[0]['title'] == 'Paper 1'
        finally:
            Path(temp_file.name).unlink()
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns empty list"""
        result = load_existing_papers_from_review_log(Path('/tmp/nonexistent.json'))
        assert result == []
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON returns empty list"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.write("{ invalid json }")
        temp_file.close()
        
        try:
            result = load_existing_papers_from_review_log(Path(temp_file.name))
            assert result == []
        finally:
            Path(temp_file.name).unlink()
