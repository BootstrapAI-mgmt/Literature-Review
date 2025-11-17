# ENHANCE-P2-2: PDF Metadata Extraction Improvements

**Status:** HEURISTIC ONLY  
**Priority:** 🟢 Low  
**Effort Estimate:** 5 hours  
**Category:** Phase 2 - Input Handling  
**Created:** November 17, 2025  
**Related PR:** #36 (Input Handling & PDF Upload)

---

## 📋 Overview

Improve PDF metadata extraction accuracy by integrating better libraries and adding new extraction capabilities (DOI, better title/abstract detection).

**Current Issues:**
- Title extraction sometimes gets first line instead of actual title
- Abstract detection is heuristic (searches for "Abstract" keyword)
- Author parsing unreliable for some PDF formats
- No DOI extraction
- Year extraction fails on some citation styles

**Impact:**
- Poor metadata quality affects gap analysis accuracy
- Manual cleanup required after upload
- Missing DOIs prevent citation tracking

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Better title extraction (use PDF metadata + heuristics)
- [ ] Improved abstract detection (multiple keyword patterns)
- [ ] DOI extraction (pattern matching + crossref lookup)
- [ ] Robust year extraction (multiple formats)

### Should Have
- [ ] Author name parsing improvements (handle "et al.", multiple formats)
- [ ] Journal/venue extraction
- [ ] Citation count extraction (if available in PDF)
- [ ] Fallback to PDF embedded metadata when text extraction fails

### Nice to Have
- [ ] Automatic title correction via DOI lookup (crossref API)
- [ ] Detect and flag low-quality extractions (confidence scores)
- [ ] Preview extraction before saving (allow manual correction)

---

## 🛠️ Technical Implementation

### 1. Library Upgrades

**Current:** PyPDF2 (basic text extraction)  
**Proposed:** PyMuPDF (fitz) or pdfplumber (better text/metadata extraction)

**Installation:**
```bash
pip install PyMuPDF  # or: pip install pdfplumber
```

**Comparison:**

| Feature | PyPDF2 | PyMuPDF | pdfplumber |
|---------|--------|---------|------------|
| Text extraction | Basic | Excellent | Excellent |
| Metadata | Limited | Comprehensive | Good |
| Speed | Fast | Very Fast | Moderate |
| Layout detection | No | Yes | Yes |
| Tables | No | Yes | Yes |

**Recommendation:** PyMuPDF for speed + quality

### 2. Enhanced Metadata Extractor

**New Module:** `literature_review/metadata_extractor.py`

```python
import fitz  # PyMuPDF
import re
from typing import Dict, Optional

class EnhancedMetadataExtractor:
    """Improved PDF metadata extraction with multiple strategies"""
    
    DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s]+')
    YEAR_PATTERNS = [
        r'\b(19|20)\d{2}\b',  # 1900-2099
        r'\((\d{4})\)',  # (2023)
        r'Published.*?(\d{4})',  # Published in 2023
    ]
    
    def __init__(self):
        self.confidence_scores = {}
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """Extract comprehensive metadata from PDF"""
        doc = fitz.open(pdf_path)
        
        # Strategy 1: Use embedded PDF metadata
        embedded_metadata = self._extract_embedded_metadata(doc)
        
        # Strategy 2: Parse first page text
        first_page_text = doc[0].get_text()
        parsed_metadata = self._parse_first_page(first_page_text)
        
        # Strategy 3: Full-text extraction for DOI/abstract
        full_text = ' '.join([page.get_text() for page in doc[:3]])  # First 3 pages
        
        # Merge strategies (prioritize most reliable)
        metadata = {
            'title': self._best_title(embedded_metadata, parsed_metadata),
            'authors': self._best_authors(embedded_metadata, parsed_metadata),
            'year': self._extract_year(first_page_text, embedded_metadata),
            'abstract': self._extract_abstract(full_text),
            'doi': self._extract_doi(full_text),
            'journal': self._extract_journal(first_page_text),
            'page_count': len(doc),
            'confidence': self.confidence_scores
        }
        
        doc.close()
        return metadata
    
    def _extract_embedded_metadata(self, doc) -> Dict:
        """Extract metadata from PDF properties"""
        metadata = doc.metadata or {}
        return {
            'title': metadata.get('title', ''),
            'authors': metadata.get('author', '').split(';'),
            'subject': metadata.get('subject', ''),
            'keywords': metadata.get('keywords', ''),
            'creator': metadata.get('creator', ''),
            'creation_date': metadata.get('creationDate', '')
        }
    
    def _parse_first_page(self, text: str) -> Dict:
        """Parse first page for metadata using heuristics"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Title heuristic: largest font size text in first 10 lines
        # (PyMuPDF can detect font sizes)
        title = self._extract_title_heuristic(lines[:10])
        
        # Authors: lines before "Abstract" or after email addresses
        authors = self._extract_authors_heuristic(lines[:20])
        
        return {
            'title': title,
            'authors': authors
        }
    
    def _extract_title_heuristic(self, lines: list) -> str:
        """Extract title from first page lines"""
        # Skip header junk (page numbers, conference names)
        skip_patterns = [r'^\d+$', r'^page \d+', r'^proceedings of']
        
        for line in lines:
            if len(line) < 10 or len(line) > 200:
                continue  # Too short or too long for title
            if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
                continue
            # Likely title if it's long enough and not all caps
            if len(line.split()) >= 3 and not line.isupper():
                self.confidence_scores['title'] = 0.8
                return line
        
        self.confidence_scores['title'] = 0.3
        return lines[0] if lines else ''
    
    def _extract_authors_heuristic(self, lines: list) -> list:
        """Extract author names from first page"""
        authors = []
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        for i, line in enumerate(lines):
            # Authors often appear before "Abstract" or after title
            if re.search(r'\b(abstract|introduction)\b', line, re.IGNORECASE):
                break
            
            # Detect author patterns: "First Last" or "F. Last"
            if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line):
                authors.append(line)
            elif re.match(r'^[A-Z]\. [A-Z][a-z]+', line):
                authors.append(line)
            
            # Stop after email addresses (end of author list)
            if re.search(email_pattern, line):
                break
        
        self.confidence_scores['authors'] = 0.7 if authors else 0.3
        return authors
    
    def _extract_year(self, text: str, embedded: Dict) -> Optional[int]:
        """Extract publication year"""
        # Try embedded metadata first
        creation_date = embedded.get('creation_date', '')
        if creation_date and len(creation_date) >= 4:
            year_match = re.search(r'(19|20)\d{2}', creation_date)
            if year_match:
                return int(year_match.group())
        
        # Parse first page for year patterns
        for pattern in self.YEAR_PATTERNS:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1) if len(match.groups()) > 0 else match.group())
                if 1900 <= year <= 2030:  # Sanity check
                    self.confidence_scores['year'] = 0.9
                    return year
        
        self.confidence_scores['year'] = 0.0
        return None
    
    def _extract_abstract(self, text: str) -> str:
        """Extract abstract with improved boundary detection"""
        # Pattern 1: "Abstract ... Introduction"
        pattern1 = r'Abstract[:\s]+(.*?)(?:Introduction|1\.|Keywords|©)'
        
        # Pattern 2: "ABSTRACT ... 1. INTRODUCTION"
        pattern2 = r'ABSTRACT[:\s]+(.*?)(?:INTRODUCTION|1\.|2\.)'
        
        # Pattern 3: Just "Abstract" to end of paragraph
        pattern3 = r'Abstract[:\s]+(.{100,1000}?)(?:\n\n|\n[A-Z])'
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                if len(abstract) > 50:  # Minimum abstract length
                    self.confidence_scores['abstract'] = 0.8
                    return abstract
        
        self.confidence_scores['abstract'] = 0.0
        return ''
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text"""
        match = self.DOI_PATTERN.search(text)
        if match:
            doi = match.group().rstrip('.,;')  # Remove trailing punctuation
            self.confidence_scores['doi'] = 0.95
            return doi
        
        self.confidence_scores['doi'] = 0.0
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """Extract journal/venue name"""
        # Common patterns
        patterns = [
            r'Published in (.*?)\n',
            r'Proceedings of (.*?)\n',
            r'Journal of (.*?),',
            r'IEEE (.*?),',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                journal = match.group(1).strip()
                self.confidence_scores['journal'] = 0.7
                return journal
        
        self.confidence_scores['journal'] = 0.0
        return None
    
    def _best_title(self, embedded: Dict, parsed: Dict) -> str:
        """Choose best title from sources"""
        embedded_title = embedded.get('title', '').strip()
        parsed_title = parsed.get('title', '').strip()
        
        # Prefer embedded if it exists and looks reasonable
        if embedded_title and len(embedded_title) > 10 and not embedded_title.endswith('.pdf'):
            return embedded_title
        
        return parsed_title or 'Unknown Title'
    
    def _best_authors(self, embedded: Dict, parsed: Dict) -> list:
        """Choose best authors from sources"""
        embedded_authors = [a.strip() for a in embedded.get('authors', []) if a.strip()]
        parsed_authors = parsed.get('authors', [])
        
        # Prefer embedded if multiple authors detected
        if len(embedded_authors) > len(parsed_authors):
            return embedded_authors
        
        return parsed_authors or ['Unknown Author']
```

### 3. Optional: DOI-based Title Correction

**Enhancement:** Verify/correct title using DOI lookup

```python
import requests

def verify_title_via_doi(doi: str, extracted_title: str) -> Dict:
    """Verify title accuracy using DOI crossref lookup"""
    try:
        response = requests.get(f'https://api.crossref.org/works/{doi}')
        if response.status_code == 200:
            data = response.json()
            crossref_title = data['message']['title'][0]
            
            # Compare similarity
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, extracted_title.lower(), crossref_title.lower()).ratio()
            
            return {
                'extracted_title': extracted_title,
                'crossref_title': crossref_title,
                'similarity': similarity,
                'should_correct': similarity < 0.8  # Low similarity = likely error
            }
    except Exception as e:
        return {'error': str(e)}
    
    return {}
```

### 4. Integration with Upload Pipeline

**Modified:** `literature_review/pdf_processor.py`

```python
from literature_review.metadata_extractor import EnhancedMetadataExtractor

def process_uploaded_pdf(file_path: str) -> Dict:
    """Process PDF with enhanced metadata extraction"""
    extractor = EnhancedMetadataExtractor()
    metadata = extractor.extract_metadata(file_path)
    
    # Optional: DOI verification
    if metadata.get('doi'):
        verification = verify_title_via_doi(metadata['doi'], metadata['title'])
        if verification.get('should_correct'):
            metadata['title_corrected'] = verification['crossref_title']
            metadata['title_original'] = metadata['title']
    
    # Flag low-confidence extractions
    low_confidence = [k for k, v in metadata['confidence'].items() if v < 0.5]
    if low_confidence:
        metadata['needs_review'] = low_confidence
    
    return metadata
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_metadata_extractor.py`

```python
def test_doi_extraction():
    """Test DOI pattern matching"""
    text = "This paper is available at DOI: 10.1234/example.2023.001"
    extractor = EnhancedMetadataExtractor()
    doi = extractor._extract_doi(text)
    
    assert doi == '10.1234/example.2023.001'

def test_year_extraction():
    """Test year extraction from various formats"""
    cases = [
        ("Published in 2023", 2023),
        ("Copyright (2022) IEEE", 2022),
        ("arXiv:2021.12345", 2021),
    ]
    
    extractor = EnhancedMetadataExtractor()
    for text, expected_year in cases:
        year = extractor._extract_year(text, {})
        assert year == expected_year

def test_abstract_extraction():
    """Test abstract boundary detection"""
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

def test_title_heuristic():
    """Test title extraction from first page lines"""
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

def test_confidence_scores():
    """Test confidence score assignment"""
    extractor = EnhancedMetadataExtractor()
    # Mock extraction with known good data
    metadata = extractor.extract_metadata('tests/fixtures/good_paper.pdf')
    
    assert metadata['confidence']['title'] > 0.7
    assert metadata['confidence']['doi'] > 0.9 if metadata['doi'] else True
```

### Integration Tests

**File:** `tests/integration/test_pdf_processing.py`

```python
def test_extract_metadata_from_real_pdf():
    """Test metadata extraction from real academic PDF"""
    # Use fixture PDF with known metadata
    pdf_path = 'tests/fixtures/sample_paper.pdf'
    
    extractor = EnhancedMetadataExtractor()
    metadata = extractor.extract_metadata(pdf_path)
    
    assert metadata['title']
    assert len(metadata['authors']) > 0
    assert metadata['year'] is not None
    assert len(metadata['abstract']) > 100

def test_fallback_to_embedded_metadata():
    """Test fallback when text extraction fails"""
    # PDF with good embedded metadata but poor text
    pdf_path = 'tests/fixtures/image_based_pdf.pdf'
    
    extractor = EnhancedMetadataExtractor()
    metadata = extractor.extract_metadata(pdf_path)
    
    # Should still extract title from embedded metadata
    assert metadata['title'] != 'Unknown Title'

def test_doi_verification():
    """Test DOI-based title verification"""
    doi = '10.1145/3291279.3341186'  # Known DOI
    extracted_title = 'Slightly Wrong Title'
    
    result = verify_title_via_doi(doi, extracted_title)
    
    assert 'crossref_title' in result
    assert result['similarity'] < 1.0  # Not exact match
```

---

## 📚 Documentation Updates

### User Guide Addition

**File:** `docs/DASHBOARD_GUIDE.md`

**New Section:**
```markdown
## PDF Metadata Extraction

### What Gets Extracted

When you upload a PDF, the system automatically extracts:

- **Title**: Paper title (from embedded metadata or first page)
- **Authors**: Author names (multiple sources)
- **Year**: Publication year
- **Abstract**: Paper abstract (if available)
- **DOI**: Digital Object Identifier (for citation tracking)
- **Journal/Venue**: Publication venue

### Extraction Methods

**Priority Order:**
1. Embedded PDF metadata (most reliable)
2. First-page text parsing (heuristic)
3. DOI crossref lookup (verification)

### Confidence Scores

Each extracted field has a confidence score (0.0-1.0):

- **0.9-1.0**: High confidence (verified via DOI or embedded metadata)
- **0.7-0.9**: Good confidence (strong heuristic match)
- **0.5-0.7**: Medium confidence (weak heuristic)
- **< 0.5**: Low confidence (flagged for review)

### Manual Review

Papers flagged for review appear with ⚠️ icon. Click to:
- View extracted vs. suggested metadata
- Manually correct title/authors
- Accept or reject automatic corrections

### Troubleshooting

**Poor Extraction Quality:**
- Scanned PDFs (images) → use OCR preprocessing
- Non-standard formats → manually enter metadata
- Missing DOI → lookup on Google Scholar and add manually

**Improving Extraction:**
- Use PDFs with text layers (not scanned images)
- Prefer papers with DOIs
- Check embedded PDF metadata before upload
```

---

## 🚀 Deployment Notes

### Dependencies

**Add to `requirements.txt`:**
```
PyMuPDF>=1.23.0  # or: pdfplumber>=0.10.0
requests>=2.31.0  # for DOI verification
```

### Performance Impact

- PyMuPDF: ~200ms per PDF (vs 100ms for PyPDF2)
- DOI verification: +500ms if enabled (optional, async recommended)
- Overall: acceptable for <50 PDFs per batch

### Configuration

**Optional Settings** (`pipeline_config.json`):
```json
{
  "metadata_extraction": {
    "use_doi_verification": true,
    "min_confidence_threshold": 0.5,
    "fallback_to_embedded": true,
    "extract_citations": false
  }
}
```

---

## 🔗 Related Issues

- PR #36: Input Handling & PDF Upload (current metadata extraction)
- ENHANCE-P2-1: Cross-Batch Duplicate Detection (uses metadata for matching)
- Future: OCR integration for scanned PDFs

---

## 📈 Success Metrics

**Quality Improvements:**
- Title accuracy: 70% → 95%
- Author detection: 60% → 85%
- DOI extraction: 0% → 80%
- Abstract extraction: 50% → 90%

**User Impact:**
- Reduced manual metadata correction time
- Better gap analysis accuracy (correct titles/abstracts)
- Citation tracking enabled (via DOIs)

---

## ✅ Definition of Done

- [ ] PyMuPDF integration implemented
- [ ] `EnhancedMetadataExtractor` class complete
- [ ] Title/author/year/abstract/DOI extraction working
- [ ] Confidence scoring implemented
- [ ] Optional DOI verification integrated
- [ ] Unit tests (≥90% coverage)
- [ ] Integration tests with real PDFs
- [ ] Documentation updated (DASHBOARD_GUIDE.md)
- [ ] Performance benchmarks (extraction time)
- [ ] Code review approved
- [ ] Merged to main branch
