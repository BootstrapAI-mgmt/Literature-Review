"""
Unit tests for Enhanced Metadata Extractor

Tests cover:
- DOI extraction from various formats
- Year extraction from multiple patterns
- Abstract boundary detection
- Title heuristic extraction
- Author name parsing
- Confidence score assignment
"""

import pytest
import re
from pathlib import Path
from literature_review.metadata_extractor import EnhancedMetadataExtractor, verify_title_via_doi


class TestDOIExtraction:
    """Tests for DOI pattern matching"""
    
    def test_doi_extraction_basic(self):
        """Test basic DOI extraction"""
        text = "This paper is available at DOI: 10.1234/example.2023.001"
        extractor = EnhancedMetadataExtractor()
        doi = extractor._extract_doi(text)
        
        assert doi == '10.1234/example.2023.001'
        assert extractor.confidence_scores['doi'] == 0.95
    
    def test_doi_extraction_with_punctuation(self):
        """Test DOI extraction with trailing punctuation"""
        text = "See DOI: 10.1145/3291279.3341186."
        extractor = EnhancedMetadataExtractor()
        doi = extractor._extract_doi(text)
        
        assert doi == '10.1145/3291279.3341186'
    
    def test_doi_extraction_url_format(self):
        """Test DOI extraction from URL format"""
        text = "https://doi.org/10.1000/xyz123"
        extractor = EnhancedMetadataExtractor()
        doi = extractor._extract_doi(text)
        
        assert doi is not None
        assert doi.startswith('10.1000')
    
    def test_doi_extraction_not_found(self):
        """Test when no DOI is present"""
        text = "This paper has no DOI identifier"
        extractor = EnhancedMetadataExtractor()
        doi = extractor._extract_doi(text)
        
        assert doi is None
        assert extractor.confidence_scores['doi'] == 0.0


class TestYearExtraction:
    """Tests for year extraction from various formats"""
    
    def test_year_extraction_plain(self):
        """Test year extraction from plain text"""
        text = "Published in 2023"
        extractor = EnhancedMetadataExtractor()
        year = extractor._extract_year(text, {})
        
        assert year == 2023
        assert extractor.confidence_scores['year'] > 0.0
    
    def test_year_extraction_parentheses(self):
        """Test year extraction from parentheses"""
        text = "Copyright (2022) IEEE"
        extractor = EnhancedMetadataExtractor()
        year = extractor._extract_year(text, {})
        
        assert year == 2022
    
    def test_year_extraction_arxiv(self):
        """Test year extraction from arXiv identifier"""
        text = "arXiv:2021.12345"
        extractor = EnhancedMetadataExtractor()
        year = extractor._extract_year(text, {})
        
        assert year == 2021
    
    def test_year_extraction_from_embedded(self):
        """Test year extraction from embedded metadata"""
        embedded = {'creation_date': 'D:20230515120000'}
        extractor = EnhancedMetadataExtractor()
        year = extractor._extract_year('', embedded)
        
        assert year == 2023
        assert extractor.confidence_scores['year'] == 0.9
    
    def test_year_extraction_invalid(self):
        """Test year extraction with invalid year"""
        text = "In the year 3000"
        extractor = EnhancedMetadataExtractor()
        year = extractor._extract_year(text, {})
        
        assert year is None  # Out of valid range
    
    def test_year_extraction_not_found(self):
        """Test when no year is found"""
        text = "No year information here"
        extractor = EnhancedMetadataExtractor()
        year = extractor._extract_year(text, {})
        
        assert year is None
        assert extractor.confidence_scores['year'] == 0.0


class TestAbstractExtraction:
    """Tests for abstract boundary detection"""
    
    def test_abstract_extraction_basic(self):
        """Test basic abstract extraction"""
        text = """
        Title of Paper
        
        Abstract
        This is the abstract of the paper. It contains important information
        about the research methodology and findings.
        
        1. Introduction
        The introduction starts here...
        """
        
        extractor = EnhancedMetadataExtractor()
        abstract = extractor._extract_abstract(text)
        
        assert 'important information' in abstract
        assert 'Introduction' not in abstract
        assert extractor.confidence_scores['abstract'] > 0.0
    
    def test_abstract_extraction_all_caps(self):
        """Test abstract extraction with all caps headers"""
        text = """
        ABSTRACT
        This paper presents a novel approach to machine learning.
        We demonstrate significant improvements over baseline methods.
        
        INTRODUCTION
        Machine learning has become...
        """
        
        extractor = EnhancedMetadataExtractor()
        abstract = extractor._extract_abstract(text)
        
        assert 'novel approach' in abstract
        assert 'INTRODUCTION' not in abstract
    
    def test_abstract_extraction_with_keywords(self):
        """Test abstract extraction stopping at Keywords"""
        text = """
        Abstract
        This is the abstract of the research paper. It contains important
        information about methodology, results, and conclusions of our study.
        
        Keywords: machine learning, AI, deep learning
        """
        
        extractor = EnhancedMetadataExtractor()
        abstract = extractor._extract_abstract(text)
        
        assert 'research paper' in abstract
        assert 'Keywords' not in abstract
    
    def test_abstract_extraction_not_found(self):
        """Test when no abstract is found"""
        text = "This paper has no abstract section"
        extractor = EnhancedMetadataExtractor()
        abstract = extractor._extract_abstract(text)
        
        assert abstract == ''
        assert extractor.confidence_scores['abstract'] == 0.0
    
    def test_abstract_extraction_too_short(self):
        """Test rejection of too-short abstracts"""
        text = """
        Abstract
        Too short.
        
        Introduction
        """
        
        extractor = EnhancedMetadataExtractor()
        abstract = extractor._extract_abstract(text)
        
        assert abstract == ''  # Should reject short extracts


class TestTitleHeuristic:
    """Tests for title extraction from first page lines"""
    
    def test_title_heuristic_basic(self):
        """Test basic title extraction"""
        lines = [
            "Proceedings of XYZ Conference",
            "",
            "A Survey of Machine Learning Techniques",
            "John Doe, Jane Smith",
            "University of Example"
        ]
        
        extractor = EnhancedMetadataExtractor()
        title = extractor._extract_title_heuristic(lines)
        
        assert title == "A Survey of Machine Learning Techniques"
        assert extractor.confidence_scores['title'] == 0.8
    
    def test_title_heuristic_skip_headers(self):
        """Test skipping common headers"""
        lines = [
            "IEEE",
            "Proceedings of ICML 2023",
            "Page 1",
            "Deep Learning for Natural Language Processing",
            "Authors: Smith et al."
        ]
        
        extractor = EnhancedMetadataExtractor()
        title = extractor._extract_title_heuristic(lines)
        
        assert title == "Deep Learning for Natural Language Processing"
    
    def test_title_heuristic_skip_all_caps(self):
        """Test skipping all-caps lines"""
        lines = [
            "CONFERENCE PROCEEDINGS",
            "A Novel Approach to Data Mining",
            "John Doe"
        ]
        
        extractor = EnhancedMetadataExtractor()
        title = extractor._extract_title_heuristic(lines)
        
        assert title == "A Novel Approach to Data Mining"
    
    def test_title_heuristic_fallback(self):
        """Test fallback to first line when no good candidate"""
        lines = [
            "123",  # Too short
            "xy",  # Too short
            "First decent line here with multiple words"
        ]
        
        extractor = EnhancedMetadataExtractor()
        title = extractor._extract_title_heuristic(lines)
        
        assert "decent line" in title


class TestAuthorHeuristic:
    """Tests for author name extraction"""
    
    def test_author_extraction_simple(self):
        """Test simple author name extraction"""
        lines = [
            "A Survey of Machine Learning",
            "John Smith",
            "University of Example",
            "Abstract"
        ]
        
        extractor = EnhancedMetadataExtractor()
        authors = extractor._extract_authors_heuristic(lines)
        
        assert "John Smith" in authors
        assert extractor.confidence_scores['authors'] == 0.7
    
    def test_author_extraction_initials(self):
        """Test author extraction with initials"""
        lines = [
            "Title Here",
            "J. Smith",
            "M. Johnson",
            "Abstract"
        ]
        
        extractor = EnhancedMetadataExtractor()
        authors = extractor._extract_authors_heuristic(lines)
        
        assert len(authors) >= 1
    
    def test_author_extraction_stop_at_abstract(self):
        """Test that extraction stops at Abstract"""
        lines = [
            "Title",
            "John Doe",
            "Abstract",
            "Jane Smith"  # Should not be extracted
        ]
        
        extractor = EnhancedMetadataExtractor()
        authors = extractor._extract_authors_heuristic(lines)
        
        assert "Jane Smith" not in authors
    
    def test_author_extraction_none_found(self):
        """Test when no authors found"""
        lines = [
            "Title of Paper",
            "123 Main St",
            "Abstract"
        ]
        
        extractor = EnhancedMetadataExtractor()
        authors = extractor._extract_authors_heuristic(lines)
        
        assert len(authors) == 0
        assert extractor.confidence_scores['authors'] == 0.3


class TestJournalExtraction:
    """Tests for journal/venue extraction"""
    
    def test_journal_extraction_published_in(self):
        """Test extraction with 'Published in' pattern"""
        text = "Published in Nature Machine Intelligence\nAuthors: Smith et al."
        extractor = EnhancedMetadataExtractor()
        journal = extractor._extract_journal(text)
        
        assert "Nature Machine Intelligence" in journal
        assert extractor.confidence_scores['journal'] == 0.7
    
    def test_journal_extraction_proceedings(self):
        """Test extraction with 'Proceedings of' pattern"""
        text = "Proceedings of ICML 2023\nMachine Learning Conference"
        extractor = EnhancedMetadataExtractor()
        journal = extractor._extract_journal(text)
        
        assert "ICML 2023" in journal
    
    def test_journal_extraction_not_found(self):
        """Test when no journal found"""
        text = "This paper has no journal information"
        extractor = EnhancedMetadataExtractor()
        journal = extractor._extract_journal(text)
        
        assert journal is None
        assert extractor.confidence_scores['journal'] == 0.0


class TestConfidenceScores:
    """Tests for confidence score assignment"""
    
    def test_confidence_scores_reset(self):
        """Test that confidence scores reset between extractions"""
        extractor = EnhancedMetadataExtractor()
        
        # First extraction
        extractor._extract_doi("DOI: 10.1234/test")
        assert 'doi' in extractor.confidence_scores
        
        # Reset and second extraction
        extractor.confidence_scores = {}
        extractor._extract_doi("No DOI here")
        assert extractor.confidence_scores['doi'] == 0.0
    
    def test_confidence_all_fields(self):
        """Test that all fields get confidence scores"""
        extractor = EnhancedMetadataExtractor()
        
        # Trigger various extractions
        extractor._extract_title_heuristic(["A Great Title About Machine Learning"])
        extractor._extract_authors_heuristic(["John Doe", "Abstract"])
        extractor._extract_year("Published in 2023", {})
        extractor._extract_abstract("Abstract\nThis is an abstract.\n\nIntroduction")
        extractor._extract_doi("DOI: 10.1234/test")
        extractor._extract_journal("Published in Nature")
        
        # Check all expected keys are present
        expected_keys = ['title', 'authors', 'year', 'abstract', 'doi', 'journal']
        for key in expected_keys:
            assert key in extractor.confidence_scores


class TestBestSelection:
    """Tests for selecting best metadata from multiple sources"""
    
    def test_best_title_prefers_embedded(self):
        """Test that embedded title is preferred"""
        extractor = EnhancedMetadataExtractor()
        embedded = {'title': 'Embedded Title From PDF Metadata'}
        parsed = {'title': 'First Line Title'}
        
        title = extractor._best_title(embedded, parsed)
        
        assert title == 'Embedded Title From PDF Metadata'
        assert extractor.confidence_scores['title'] == 0.9
    
    def test_best_title_rejects_pdf_filename(self):
        """Test that PDF filename in embedded title is rejected"""
        extractor = EnhancedMetadataExtractor()
        embedded = {'title': 'paper123.pdf'}
        parsed = {'title': 'Actual Paper Title'}
        
        title = extractor._best_title(embedded, parsed)
        
        assert title == 'Actual Paper Title'
    
    def test_best_authors_prefers_more(self):
        """Test that more authors are preferred"""
        extractor = EnhancedMetadataExtractor()
        embedded = {'authors': ['John Doe', 'Jane Smith', 'Bob Johnson']}
        parsed = {'authors': ['John Doe']}
        
        authors = extractor._best_authors(embedded, parsed)
        
        assert len(authors) == 3
        assert extractor.confidence_scores['authors'] == 0.8


# Note: Integration tests with actual PDFs would go in test_pdf_processing.py
# These unit tests focus on testing individual methods with text inputs
