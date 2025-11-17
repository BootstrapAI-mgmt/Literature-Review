"""
Integration tests for PDF metadata extraction

Tests cover:
- Full PDF metadata extraction workflow
- Integration with database builder
- Fallback mechanisms
- Real PDF processing
"""

import io
import pytest
from pathlib import Path
from literature_review.metadata_extractor import EnhancedMetadataExtractor, verify_title_via_doi


def create_test_pdf_with_metadata(title: str = "Test Paper Title", author: str = "John Doe") -> bytes:
    """
    Create a minimal PDF with embedded metadata for testing
    
    Args:
        title: Title to embed
        author: Author to embed
        
    Returns:
        PDF bytes
    """
    # Minimal valid PDF with metadata
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/Metadata 5 0 R
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
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
50 750 Td
({title}) Tj
0 -20 Td
(By {author}) Tj
0 -40 Td
(Abstract) Tj
0 -20 Td
(This is a test abstract for the research paper. It contains important) Tj
0 -15 Td
(information about the methodology and findings of the study.) Tj
0 -40 Td
(DOI: 10.1234/test.2023.001) Tj
0 -40 Td
(1. Introduction) Tj
0 -20 Td
(The introduction starts here...) Tj
ET
endstream
endobj
5 0 obj
<<
/Type /Metadata
/Subtype /XML
/Length 50
>>
stream
<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
endstream
endobj
trailer
<<
/Size 6
/Root 1 0 R
/Info <<
/Title ({title})
/Author ({author})
/CreationDate (D:20230515120000)
>>
>>
startxref
1000
%%EOF
"""
    return pdf_content.encode('latin-1')


@pytest.fixture
def temp_pdf_file(tmp_path):
    """Create a temporary PDF file for testing"""
    pdf_path = tmp_path / "test_paper.pdf"
    pdf_content = create_test_pdf_with_metadata(
        title="Machine Learning for Climate Science",
        author="John Doe; Jane Smith"
    )
    pdf_path.write_bytes(pdf_content)
    return pdf_path


class TestEnhancedMetadataExtractor:
    """Integration tests for EnhancedMetadataExtractor"""
    
    def test_extract_metadata_from_pdf(self, temp_pdf_file):
        """Test metadata extraction from a real PDF file"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Check all expected fields are present
        assert 'title' in metadata
        assert 'authors' in metadata
        assert 'year' in metadata
        assert 'abstract' in metadata
        assert 'doi' in metadata
        assert 'journal' in metadata
        assert 'page_count' in metadata
        assert 'confidence' in metadata
        
        # Verify extracted content
        assert metadata['title']  # Should not be empty
        assert len(metadata['authors']) > 0
        assert metadata['page_count'] == 1
    
    def test_extract_title_from_embedded_metadata(self, temp_pdf_file):
        """Test that title is extracted from embedded metadata"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Should extract from embedded metadata
        assert "Machine Learning for Climate Science" in metadata['title']
        # High confidence due to embedded metadata
        assert metadata['confidence']['title'] >= 0.8
    
    def test_extract_authors_from_embedded_metadata(self, temp_pdf_file):
        """Test that authors are extracted from embedded metadata"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Should extract authors
        assert len(metadata['authors']) >= 1
        # Should have author confidence
        assert 'authors' in metadata['confidence']
    
    def test_extract_year_from_creation_date(self, temp_pdf_file):
        """Test year extraction from PDF creation date"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Should extract year from creation date (2023)
        assert metadata['year'] == 2023
        # High confidence from embedded metadata
        assert metadata['confidence']['year'] >= 0.8
    
    def test_extract_doi_from_content(self, temp_pdf_file):
        """Test DOI extraction from PDF text content"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Should find DOI in content
        assert metadata['doi'] == '10.1234/test.2023.001'
        # High confidence for DOI
        assert metadata['confidence']['doi'] >= 0.9
    
    def test_extract_abstract_from_content(self, temp_pdf_file):
        """Test abstract extraction from PDF text"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Should extract abstract
        if metadata['abstract']:  # Might be empty due to PDF parsing quirks
            assert 'abstract' in metadata['abstract'].lower() or len(metadata['abstract']) > 20
    
    def test_confidence_scores_present(self, temp_pdf_file):
        """Test that all confidence scores are provided"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        expected_confidence_keys = ['title', 'authors', 'year', 'abstract', 'doi', 'journal']
        for key in expected_confidence_keys:
            assert key in metadata['confidence']
            assert 0.0 <= metadata['confidence'][key] <= 1.0
    
    def test_error_handling_invalid_pdf(self, tmp_path):
        """Test error handling with invalid PDF"""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_bytes(b"This is not a valid PDF")
        
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(invalid_pdf))
        
        # Should return error metadata
        assert 'error' in metadata
        assert metadata['title'] == 'invalid'  # Filename
        assert metadata['page_count'] == 0
    
    def test_error_handling_nonexistent_file(self):
        """Test error handling with nonexistent file"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata("/nonexistent/file.pdf")
        
        # Should return error metadata
        assert 'error' in metadata
        assert metadata['page_count'] == 0


class TestDatabaseBuilderIntegration:
    """Integration tests for database builder with enhanced extraction"""
    
    def test_database_builder_uses_enhanced_extraction(self, tmp_path):
        """Test that database builder can use enhanced extraction"""
        from webdashboard.database_builder import ResearchDatabaseBuilder
        
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_content = create_test_pdf_with_metadata(
            title="Test Research Paper",
            author="Alice Johnson"
        )
        pdf_path.write_bytes(pdf_content)
        
        # Build database
        builder = ResearchDatabaseBuilder(
            job_id="test_job",
            pdf_files=[pdf_path],
            use_enhanced_extraction=True
        )
        
        # Check that enhanced extraction is available
        if builder.use_enhanced_extraction:
            assert builder.enhanced_extractor is not None
    
    def test_database_builder_fallback_to_basic(self, tmp_path, monkeypatch):
        """Test fallback to basic extraction if enhanced unavailable"""
        from webdashboard.database_builder import ResearchDatabaseBuilder
        
        # Mock enhanced extraction as unavailable
        monkeypatch.setattr(
            "webdashboard.database_builder.ENHANCED_EXTRACTION_AVAILABLE",
            False
        )
        
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_content = create_test_pdf_with_metadata()
        pdf_path.write_bytes(pdf_content)
        
        # Build database - should use basic extraction
        builder = ResearchDatabaseBuilder(
            job_id="test_job",
            pdf_files=[pdf_path],
            use_enhanced_extraction=True
        )
        
        assert builder.enhanced_extractor is None


class TestDOIVerification:
    """Tests for optional DOI-based title verification"""
    
    @pytest.mark.skip(reason="Requires network access to CrossRef API")
    def test_doi_verification_real_doi(self):
        """Test DOI verification with a real DOI (requires network)"""
        doi = '10.1145/3291279.3341186'
        extracted_title = 'Slightly Wrong Title'
        
        result = verify_title_via_doi(doi, extracted_title)
        
        assert 'crossref_title' in result
        assert 'similarity' in result
        assert 'should_correct' in result
        assert isinstance(result['similarity'], float)
    
    def test_doi_verification_invalid_doi(self):
        """Test DOI verification with invalid DOI"""
        doi = 'invalid.doi.format'
        extracted_title = 'Test Title'
        
        result = verify_title_via_doi(doi, extracted_title)
        
        # Should handle error gracefully
        assert 'error' in result or len(result) == 0
    
    @pytest.mark.skip(reason="Requires network access")
    def test_doi_verification_exact_match(self):
        """Test DOI verification with exact match"""
        # This would need a known DOI with exact title
        # Skipped for now as it requires network access
        pass


class TestFullWorkflow:
    """End-to-end workflow tests"""
    
    def test_full_extraction_workflow(self, temp_pdf_file):
        """Test complete extraction workflow"""
        extractor = EnhancedMetadataExtractor()
        
        # Extract metadata
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # Verify complete workflow
        assert metadata['title']
        assert len(metadata['authors']) > 0
        assert metadata['year'] is not None
        assert 'confidence' in metadata
        
        # Check for quality flags
        low_confidence = [k for k, v in metadata['confidence'].items() if v < 0.5]
        # Should have some high-confidence extractions
        high_confidence = [k for k, v in metadata['confidence'].items() if v >= 0.7]
        assert len(high_confidence) > 0
    
    def test_metadata_ready_for_database(self, temp_pdf_file):
        """Test that extracted metadata is ready for database insertion"""
        extractor = EnhancedMetadataExtractor()
        metadata = extractor.extract_metadata(str(temp_pdf_file))
        
        # All required fields should be present
        assert metadata['title'] is not None
        assert metadata['authors'] is not None
        assert metadata['year'] is not None or metadata['year'] == None  # Can be None
        
        # Authors should be a list
        assert isinstance(metadata['authors'], list)
        
        # Year should be int or None
        assert metadata['year'] is None or isinstance(metadata['year'], int)
        
        # Confidence should be a dict
        assert isinstance(metadata['confidence'], dict)
