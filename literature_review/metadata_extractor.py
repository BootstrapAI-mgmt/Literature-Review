"""
Enhanced PDF Metadata Extraction Module

Provides improved metadata extraction from PDF files using PyMuPDF (fitz)
with multiple extraction strategies and confidence scoring.

This module replaces basic PyPDF2 extraction with more robust methods:
- Embedded PDF metadata extraction
- First-page text parsing with heuristics
- DOI pattern matching
- Abstract boundary detection
- Multiple year format support
- Confidence scoring for quality assessment
"""

import re
import logging
from typing import Dict, Optional, List
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)


class EnhancedMetadataExtractor:
    """Improved PDF metadata extraction with multiple strategies"""
    
    # Regular expression patterns
    DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s\]]+')
    YEAR_PATTERNS = [
        r'\b(19|20)\d{2}\b',  # 1900-2099
        r'\((\d{4})\)',  # (2023)
        r'Published.*?(\d{4})',  # Published in 2023
        r'Copyright.*?(\d{4})',  # Copyright 2023
        r'arXiv:(\d{4})',  # arXiv:2021
    ]
    
    # Patterns to skip when looking for title
    SKIP_TITLE_PATTERNS = [
        r'^\d+$',  # Just a number
        r'^page\s*\d+',  # Page numbers
        r'^proceedings\s+of',  # Conference proceedings header
        r'^ieee',  # IEEE header
        r'^acm',  # ACM header
        r'^springer',  # Springer header
        r'^\w+@\w+\.',  # Email addresses
    ]
    
    def __init__(self):
        """Initialize the metadata extractor"""
        if fitz is None:
            raise ImportError(
                "PyMuPDF is required for enhanced metadata extraction. "
                "Install with: pip install PyMuPDF"
            )
        self.confidence_scores = {}
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """
        Extract comprehensive metadata from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing extracted metadata with confidence scores
        """
        self.confidence_scores = {}  # Reset for each extraction
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            return self._create_error_metadata(pdf_path, str(e))
        
        try:
            # Strategy 1: Extract embedded PDF metadata
            embedded_metadata = self._extract_embedded_metadata(doc)
            
            # Strategy 2: Parse first page text
            first_page_text = ""
            if len(doc) > 0:
                first_page_text = doc[0].get_text()
            parsed_metadata = self._parse_first_page(first_page_text)
            
            # Strategy 3: Full-text extraction for DOI/abstract (first 3 pages)
            full_text = ' '.join([doc[i].get_text() for i in range(min(3, len(doc)))])
            
            # Merge strategies (prioritize most reliable)
            metadata = {
                'title': self._best_title(embedded_metadata, parsed_metadata),
                'authors': self._best_authors(embedded_metadata, parsed_metadata),
                'year': self._extract_year(first_page_text, embedded_metadata),
                'abstract': self._extract_abstract(full_text),
                'doi': self._extract_doi(full_text),
                'journal': self._extract_journal(first_page_text),
                'page_count': len(doc),
                'confidence': self.confidence_scores.copy()
            }
            
            doc.close()
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_path}: {e}")
            doc.close()
            return self._create_error_metadata(pdf_path, str(e))
    
    def _extract_embedded_metadata(self, doc) -> Dict:
        """
        Extract metadata from PDF properties
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            Dictionary of embedded metadata
        """
        metadata = doc.metadata or {}
        return {
            'title': metadata.get('title', ''),
            'authors': metadata.get('author', '').split(';') if metadata.get('author') else [],
            'subject': metadata.get('subject', ''),
            'keywords': metadata.get('keywords', ''),
            'creator': metadata.get('creator', ''),
            'creation_date': metadata.get('creationDate', '')
        }
    
    def _parse_first_page(self, text: str) -> Dict:
        """
        Parse first page for metadata using heuristics
        
        Args:
            text: First page text content
            
        Returns:
            Dictionary with parsed title and authors
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract title and authors using heuristics
        title = self._extract_title_heuristic(lines[:10])
        authors = self._extract_authors_heuristic(lines[:20])
        
        return {
            'title': title,
            'authors': authors
        }
    
    def _extract_title_heuristic(self, lines: List[str]) -> str:
        """
        Extract title from first page lines using heuristics
        
        Args:
            lines: First lines from the PDF
            
        Returns:
            Extracted title string
        """
        for line in lines:
            # Skip lines that are too short or too long
            if len(line) < 10 or len(line) > 200:
                continue
            
            # Skip header junk
            if any(re.match(p, line, re.IGNORECASE) for p in self.SKIP_TITLE_PATTERNS):
                continue
            
            # Likely title if it has multiple words and not all caps
            if len(line.split()) >= 3 and not line.isupper():
                self.confidence_scores['title'] = 0.8
                return line
        
        # Fallback to first non-empty line
        self.confidence_scores['title'] = 0.3
        return lines[0] if lines else ''
    
    def _extract_authors_heuristic(self, lines: List[str]) -> List[str]:
        """
        Extract author names from first page
        
        Args:
            lines: First lines from the PDF
            
        Returns:
            List of author names
        """
        authors = []
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        for line in lines:
            # Stop at abstract or introduction
            if re.search(r'\b(abstract|introduction)\b', line, re.IGNORECASE):
                break
            
            # Detect author patterns: "First Last" or "F. Last" or "First M. Last"
            if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line):
                authors.append(line)
            elif re.match(r'^[A-Z]\. [A-Z][a-z]+', line):
                authors.append(line)
            elif ', and ' in line or ' and ' in line:
                # Handle "Author1, Author2, and Author3" format
                parts = re.split(r',?\s+and\s+|,\s+', line)
                authors.extend([p.strip() for p in parts if len(p.strip()) > 3])
            
            # Stop after email addresses (end of author list)
            if re.search(email_pattern, line):
                break
        
        self.confidence_scores['authors'] = 0.7 if authors else 0.3
        return authors
    
    def _extract_year(self, text: str, embedded: Dict) -> Optional[int]:
        """
        Extract publication year from multiple sources
        
        Args:
            text: PDF text content
            embedded: Embedded metadata dictionary
            
        Returns:
            Publication year as integer or None
        """
        # Try embedded metadata first
        creation_date = embedded.get('creation_date', '')
        if creation_date and len(creation_date) >= 4:
            year_match = re.search(r'(19|20)\d{2}', creation_date)
            if year_match:
                year = int(year_match.group())
                if 1900 <= year <= 2030:  # Sanity check
                    self.confidence_scores['year'] = 0.9
                    return year
        
        # Parse first page for year patterns
        for pattern in self.YEAR_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Extract year from match (handle groups)
                for match in matches:
                    if isinstance(match, tuple):
                        year_str = ''.join(match)
                    else:
                        year_str = match
                    
                    year_match = re.search(r'\d{4}', year_str)
                    if year_match:
                        year = int(year_match.group())
                        if 1900 <= year <= 2030:  # Sanity check
                            self.confidence_scores['year'] = 0.8
                            return year
        
        self.confidence_scores['year'] = 0.0
        return None
    
    def _extract_abstract(self, text: str) -> str:
        """
        Extract abstract with improved boundary detection
        
        Args:
            text: PDF text content
            
        Returns:
            Extracted abstract text
        """
        # Pattern 1: "Abstract ... Introduction" or "Abstract ... 1."
        pattern1 = r'Abstract[:\s]+(.*?)(?:Introduction|1\.|2\.|Keywords|©)'
        
        # Pattern 2: "ABSTRACT ... INTRODUCTION" (all caps)
        pattern2 = r'ABSTRACT[:\s]+(.*?)(?:INTRODUCTION|1\.|2\.|Keywords)'
        
        # Pattern 3: Just "Abstract" to end of paragraph
        pattern3 = r'Abstract[:\s]+(.{100,1500}?)(?:\n\n|\n[A-Z][a-z]+:)'
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up whitespace
                abstract = re.sub(r'\s+', ' ', abstract)
                if len(abstract) > 50:  # Minimum abstract length
                    self.confidence_scores['abstract'] = 0.8
                    return abstract
        
        self.confidence_scores['abstract'] = 0.0
        return ''
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """
        Extract DOI from text using pattern matching
        
        Args:
            text: PDF text content
            
        Returns:
            DOI string or None
        """
        # Look for DOI pattern
        match = self.DOI_PATTERN.search(text)
        if match:
            doi = match.group().rstrip('.,;')  # Remove trailing punctuation
            self.confidence_scores['doi'] = 0.95
            return doi
        
        self.confidence_scores['doi'] = 0.0
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """
        Extract journal/venue name from text
        
        Args:
            text: PDF text content
            
        Returns:
            Journal/venue name or None
        """
        # Common patterns for journal/venue names
        patterns = [
            r'Published in (.*?)[\n,]',
            r'Proceedings of (.*?)[\n,]',
            r'Journal of (.*?)[\n,]',
            r'IEEE (.*?)[\n,]',
            r'ACM (.*?)[\n,]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                journal = match.group(1).strip()
                if len(journal) > 3 and len(journal) < 200:
                    self.confidence_scores['journal'] = 0.7
                    return journal
        
        self.confidence_scores['journal'] = 0.0
        return None
    
    def _best_title(self, embedded: Dict, parsed: Dict) -> str:
        """
        Choose best title from multiple sources
        
        Args:
            embedded: Embedded metadata dictionary
            parsed: Parsed metadata dictionary
            
        Returns:
            Best title string
        """
        embedded_title = embedded.get('title', '').strip()
        parsed_title = parsed.get('title', '').strip()
        
        # Prefer embedded if it exists and looks reasonable
        if embedded_title and len(embedded_title) > 10 and not embedded_title.endswith('.pdf'):
            # Boost confidence if we have embedded title
            if 'title' in self.confidence_scores:
                self.confidence_scores['title'] = max(self.confidence_scores['title'], 0.9)
            else:
                self.confidence_scores['title'] = 0.9
            return embedded_title
        
        return parsed_title or 'Unknown Title'
    
    def _best_authors(self, embedded: Dict, parsed: Dict) -> List[str]:
        """
        Choose best authors from multiple sources
        
        Args:
            embedded: Embedded metadata dictionary
            parsed: Parsed metadata dictionary
            
        Returns:
            List of author names
        """
        embedded_authors = [a.strip() for a in embedded.get('authors', []) if a.strip()]
        parsed_authors = parsed.get('authors', [])
        
        # Prefer embedded if multiple authors detected
        if len(embedded_authors) > len(parsed_authors):
            if 'authors' in self.confidence_scores:
                self.confidence_scores['authors'] = max(self.confidence_scores['authors'], 0.8)
            else:
                self.confidence_scores['authors'] = 0.8
            return embedded_authors
        
        return parsed_authors or ['Unknown Author']
    
    def _create_error_metadata(self, pdf_path: str, error_msg: str) -> Dict:
        """
        Create placeholder metadata when extraction fails
        
        Args:
            pdf_path: Path to PDF file
            error_msg: Error message
            
        Returns:
            Dictionary with minimal metadata
        """
        filename = Path(pdf_path).stem
        return {
            'title': filename,
            'authors': ['Unknown Author'],
            'year': None,
            'abstract': '',
            'doi': None,
            'journal': None,
            'page_count': 0,
            'confidence': {
                'title': 0.0,
                'authors': 0.0,
                'year': 0.0,
                'abstract': 0.0,
                'doi': 0.0,
                'journal': 0.0
            },
            'error': error_msg
        }


def verify_title_via_doi(doi: str, extracted_title: str) -> Dict:
    """
    Verify title accuracy using DOI crossref lookup
    
    This is an optional enhancement that can be used to validate
    extracted titles against the official CrossRef database.
    
    Args:
        doi: Digital Object Identifier
        extracted_title: Title extracted from PDF
        
    Returns:
        Dictionary with verification results
    """
    try:
        import requests
        from difflib import SequenceMatcher
        
        response = requests.get(
            f'https://api.crossref.org/works/{doi}',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            crossref_title = data['message']['title'][0]
            
            # Compare similarity
            similarity = SequenceMatcher(
                None, 
                extracted_title.lower(), 
                crossref_title.lower()
            ).ratio()
            
            return {
                'extracted_title': extracted_title,
                'crossref_title': crossref_title,
                'similarity': similarity,
                'should_correct': similarity < 0.8  # Low similarity = likely error
            }
    except Exception as e:
        logger.warning(f"DOI verification failed for {doi}: {e}")
        return {'error': str(e)}
    
    return {}
