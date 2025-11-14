"""
Unit Tests for Provenance Tracking Functions
Tests section detection, provenance addition, and page-level extraction.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.reviewers.journal_reviewer import (
    detect_section_heading,
    add_provenance_to_claim,
    extract_text_with_provenance
)


class TestSectionHeadingDetection:
    """Test suite for detect_section_heading function."""
    
    @pytest.mark.unit
    def test_detects_numbered_introduction(self):
        """Test detection of numbered introduction heading."""
        text_intro = "1. Introduction\n\nThis paper presents..."
        assert detect_section_heading(text_intro) == "Introduction"
    
    @pytest.mark.unit
    def test_detects_uppercase_methods(self):
        """Test detection of uppercase methods heading."""
        text_methods = "METHODS\n\nWe used the following approach..."
        assert detect_section_heading(text_methods) == "Methods"
    
    @pytest.mark.unit
    def test_detects_numbered_with_space(self):
        """Test detection of numbered heading with space."""
        text = "2 Results\n\nOur experiments showed..."
        assert detect_section_heading(text) == "Results"
    
    @pytest.mark.unit
    def test_detects_results_section(self):
        """Test detection of results section."""
        text = "3. Results\n\nThe evaluation demonstrates..."
        assert detect_section_heading(text) == "Results"
    
    @pytest.mark.unit
    def test_detects_discussion_section(self):
        """Test detection of discussion section."""
        text = "Discussion\n\nOur findings suggest..."
        assert detect_section_heading(text) == "Discussion"
    
    @pytest.mark.unit
    def test_no_heading_detected(self):
        """Test that None is returned when no heading is found."""
        text_no_heading = "This is body text without a heading at the start..."
        assert detect_section_heading(text_no_heading) is None
    
    @pytest.mark.unit
    def test_detects_abstract(self):
        """Test detection of abstract section."""
        text = "Abstract\n\nThis paper explores..."
        assert detect_section_heading(text) == "Abstract"
    
    @pytest.mark.unit
    def test_detects_conclusion(self):
        """Test detection of conclusion section."""
        text = "5. Conclusion\n\nIn this work we..."
        assert detect_section_heading(text) == "Conclusion"


class TestProvenanceAddition:
    """Test suite for add_provenance_to_claim function."""
    
    @pytest.mark.unit
    def test_adds_provenance_to_claim(self):
        """Test adding provenance to claim with exact match."""
        full_text = "Some intro text. The key finding is that SNNs achieve 95% accuracy. More text follows here."
        pages_metadata = [
            {
                "page_num": 1,
                "section": "Results",
                "char_start": 0,
                "char_end": len(full_text)
            }
        ]
        
        claim = {"extracted_claim_text": "SNNs achieve 95% accuracy"}
        evidence_text = "SNNs achieve 95% accuracy"
        
        enhanced_claim = add_provenance_to_claim(claim, full_text, pages_metadata, evidence_text)
        
        assert "provenance" in enhanced_claim
        assert enhanced_claim["provenance"]["page_numbers"] == [1]
        assert enhanced_claim["provenance"]["section"] == "Results"
        assert "The key finding is that" in enhanced_claim["provenance"]["context_before"]
        assert "More text follows" in enhanced_claim["provenance"]["context_after"]
    
    @pytest.mark.unit
    def test_handles_missing_evidence(self):
        """Test that claim is unchanged when evidence not found."""
        full_text = "Some text that doesn't contain the evidence."
        pages_metadata = [
            {"page_num": 1, "section": "Introduction", "char_start": 0, "char_end": len(full_text)}
        ]
        
        claim = {"extracted_claim_text": "Some claim"}
        evidence_text = "Non-existent evidence text"
        
        enhanced_claim = add_provenance_to_claim(claim, full_text, pages_metadata, evidence_text)
        
        # Claim should be returned unchanged (no provenance added)
        assert enhanced_claim == claim
    
    @pytest.mark.unit
    def test_handles_multi_page_evidence(self):
        """Test provenance for evidence spanning multiple pages."""
        page1_text = "This is page 1 with the start of evidence: The network "
        page2_text = "achieved 98% accuracy on the benchmark dataset."
        full_text = page1_text + page2_text
        
        pages_metadata = [
            {"page_num": 1, "section": "Results", "char_start": 0, "char_end": len(page1_text)},
            {"page_num": 2, "section": "Results", "char_start": len(page1_text), "char_end": len(full_text)}
        ]
        
        claim = {"extracted_claim_text": "Network accuracy"}
        evidence_text = "The network achieved 98% accuracy"
        
        enhanced_claim = add_provenance_to_claim(claim, full_text, pages_metadata, evidence_text)
        
        assert "provenance" in enhanced_claim
        # Should detect both pages
        assert 1 in enhanced_claim["provenance"]["page_numbers"]
        assert enhanced_claim["provenance"]["section"] == "Results"
    
    @pytest.mark.unit
    def test_truncates_long_quotes(self):
        """Test that long supporting quotes are truncated."""
        long_evidence = "A" * 600  # Create a string longer than 500 chars
        full_text = f"Introduction. {long_evidence} Conclusion."
        pages_metadata = [
            {"page_num": 1, "section": "Methods", "char_start": 0, "char_end": len(full_text)}
        ]
        
        claim = {"extracted_claim_text": "Long claim"}
        enhanced_claim = add_provenance_to_claim(claim, full_text, pages_metadata, long_evidence)
        
        assert "provenance" in enhanced_claim
        # Quote should be truncated to 500 chars
        assert len(enhanced_claim["provenance"]["supporting_quote"]) == 500
    
    @pytest.mark.unit
    def test_extracts_context(self):
        """Test that context before and after is extracted correctly."""
        full_text = "X" * 150 + "EVIDENCE" + "Y" * 150
        pages_metadata = [
            {"page_num": 1, "section": "Discussion", "char_start": 0, "char_end": len(full_text)}
        ]
        
        claim = {"extracted_claim_text": "Test"}
        evidence_text = "EVIDENCE"
        
        enhanced_claim = add_provenance_to_claim(claim, full_text, pages_metadata, evidence_text)
        
        assert "provenance" in enhanced_claim
        # Context should be trimmed to 100 chars
        assert len(enhanced_claim["provenance"]["context_before"]) <= 100
        assert len(enhanced_claim["provenance"]["context_after"]) <= 100


class TestExtractTextWithProvenance:
    """Test suite for extract_text_with_provenance function."""
    
    @pytest.mark.unit
    @patch('literature_review.reviewers.journal_reviewer.pdfplumber')
    def test_extracts_pages_with_metadata(self, mock_pdfplumber):
        """Test that pages are extracted with correct metadata."""
        # Mock PDF with 2 pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "1. Introduction\nThis is page 1 text."
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "2. Methods\nThis is page 2 text."
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = extract_text_with_provenance("test.pdf")
        
        assert len(result) == 2
        assert result[0]["page_num"] == 1
        assert result[0]["section"] == "Introduction"
        assert result[0]["char_start"] == 0
        assert "page 1 text" in result[0]["text"]
        
        assert result[1]["page_num"] == 2
        assert result[1]["section"] == "Methods"
        assert result[1]["char_start"] == len(result[0]["text"])
    
    @pytest.mark.unit
    @patch('literature_review.reviewers.journal_reviewer.pdfplumber')
    def test_handles_empty_pages(self, mock_pdfplumber):
        """Test handling of pages with no extractable text."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = None
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Some text on page 2"
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = extract_text_with_provenance("test.pdf")
        
        assert len(result) == 2
        assert result[0]["text"] == ""
        assert result[1]["text"] == "Some text on page 2"
    
    @pytest.mark.unit
    @patch('literature_review.reviewers.journal_reviewer.pdfplumber')
    def test_cumulative_char_offsets(self, mock_pdfplumber):
        """Test that character offsets are cumulative across pages."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "A" * 100
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "B" * 50
        
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "C" * 75
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = extract_text_with_provenance("test.pdf")
        
        assert result[0]["char_start"] == 0
        assert result[0]["char_end"] == 100
        assert result[1]["char_start"] == 100
        assert result[1]["char_end"] == 150
        assert result[2]["char_start"] == 150
        assert result[2]["char_end"] == 225
    
    @pytest.mark.unit
    @patch('literature_review.reviewers.journal_reviewer.pdfplumber')
    @patch('literature_review.reviewers.journal_reviewer.logger')
    def test_handles_extraction_error(self, mock_logger, mock_pdfplumber):
        """Test error handling when PDF extraction fails."""
        mock_pdfplumber.open.side_effect = Exception("PDF extraction failed")
        
        result = extract_text_with_provenance("invalid.pdf")
        
        assert result == []
        mock_logger.error.assert_called_once()
