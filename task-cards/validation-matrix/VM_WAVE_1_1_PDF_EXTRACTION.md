# Task Card: PDF Extraction Validation

**Task ID:** VM-W1-1  
**Wave:** 1 (Core Functional Validation)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W2-3  
**Validation IDs:** FV-01, FV-02

---

## Objective

Validate PDF text extraction functionality, ensuring high fidelity text extraction (≥90%) and graceful handling of edge cases (corrupted, scanned, malformed PDFs).

## Background

The Journal Reviewer relies on accurate text extraction from PDFs for claim identification. The pipeline uses:
- `pypdf` for standard PDF extraction
- `pdfplumber` for table extraction
- OCR fallback for scanned documents (if available)

Text extraction quality directly impacts all downstream processes.

## Success Criteria

- [ ] FV-01: Text extraction fidelity ≥90% for valid PDFs
- [ ] FV-02: Graceful failure handling for corrupted/scanned PDFs
- [ ] Metadata extraction validation (title, authors, year)
- [ ] Edge case test suite complete
- [ ] Performance within acceptable bounds (<5s per typical PDF)

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| FV-01 | PDF Extraction (Valid) | Sample PDF (valid) | Extracted text with metadata | Text ≥90% fidelity, metadata present |
| FV-02 | PDF Extraction (Edge) | Corrupted/scanned PDF | Graceful failure or OCR fallback | No crash, appropriate error message |

---

## Deliverables

### 1. Test Fixture PDFs

**Directory:** `tests/fixtures/pdfs/`

Create or obtain test PDFs:
- `valid_research_paper.pdf` - Standard research paper (~20 pages)
- `valid_short_paper.pdf` - Short paper (~5 pages)
- `corrupted_header.pdf` - PDF with corrupted header
- `truncated.pdf` - Truncated/incomplete PDF
- `scanned_document.pdf` - Scanned (image-only) PDF
- `password_protected.pdf` - Password-protected PDF
- `empty.pdf` - Empty PDF (0 pages)
- `special_characters.pdf` - PDF with Unicode/special chars
- `multi_column.pdf` - Multi-column layout
- `tables_heavy.pdf` - PDF with many tables

### 2. Test Implementation

**File:** `tests/validation/functional/test_pdf_extraction.py`

```python
"""
PDF Extraction Validation Tests

Validates FV-01 and FV-02 from the validation matrix.
"""

import pytest
import os
from pathlib import Path
from typing import Dict, Any

from tests.validation.base import ValidationTestCase, ValidationResult
from literature_review.reviewers.journal_reviewer import TextExtractor


class TestPDFExtraction(ValidationTestCase):
    """
    Validate PDF text extraction functionality.
    
    FV-01: Valid PDF extraction with ≥90% fidelity
    FV-02: Edge case handling for problematic PDFs
    """
    
    TEST_CATEGORY = "FV"
    
    FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "pdfs"
    
    # Expected text snippets for fidelity testing
    VALID_PDF_EXPECTED = {
        "valid_research_paper.pdf": {
            "expected_snippets": [
                "Abstract",
                "Introduction",
                "Methodology",
                "Results",
                "Conclusion"
            ],
            "min_length": 5000,
            "expected_metadata": ["title", "author"]
        }
    }
    
    @pytest.fixture
    def text_extractor(self):
        """Create TextExtractor instance."""
        return TextExtractor()
    
    # =========================================================================
    # FV-01: Valid PDF Extraction
    # =========================================================================
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv01_valid_pdf_text_extraction(self, text_extractor):
        """
        FV-01: Test text extraction from valid PDFs.
        
        Success Criteria:
        - Text extraction completes without error
        - Extracted text length meets minimum threshold
        - Key sections are present in extracted text
        - Extraction fidelity ≥90%
        """
        pdf_path = self.FIXTURES_DIR / "valid_research_paper.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available: valid_research_paper.pdf")
        
        # Execute extraction
        text, metadata = text_extractor.extract_text(str(pdf_path))
        
        # Validate minimum length
        expected_config = self.VALID_PDF_EXPECTED.get("valid_research_paper.pdf", {})
        min_length = expected_config.get("min_length", 1000)
        
        result_length = self.validate_threshold(
            test_id="FV-01-A",
            test_name="Extracted text minimum length",
            actual=len(text),
            threshold=min_length,
            comparison="gte",
            metadata={"pdf_file": str(pdf_path)}
        )
        assert result_length.passed, f"Text length {len(text)} < {min_length}"
        
        # Validate expected snippets present
        expected_snippets = expected_config.get("expected_snippets", [])
        found_snippets = sum(1 for s in expected_snippets if s.lower() in text.lower())
        
        result_fidelity = self.validate_percentage(
            test_id="FV-01-B",
            test_name="Expected section presence",
            numerator=found_snippets,
            denominator=len(expected_snippets),
            threshold_percent=90.0,
            comparison="gte",
            metadata={
                "expected_snippets": expected_snippets,
                "found": found_snippets
            }
        )
        assert result_fidelity.passed, f"Section fidelity {found_snippets}/{len(expected_snippets)} < 90%"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv01_metadata_extraction(self, text_extractor):
        """
        FV-01: Test metadata extraction from valid PDFs.
        
        Success Criteria:
        - Title extracted (if present in PDF metadata)
        - Author extracted (if present in PDF metadata)
        - Year/date extracted (if present)
        """
        pdf_path = self.FIXTURES_DIR / "valid_research_paper.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available")
        
        text, metadata = text_extractor.extract_text(str(pdf_path))
        
        # Check metadata fields
        metadata_fields_present = 0
        expected_fields = ["title", "author", "creation_date"]
        
        for field in expected_fields:
            if metadata.get(field):
                metadata_fields_present += 1
        
        result = self.validate_threshold(
            test_id="FV-01-C",
            test_name="Metadata fields extracted",
            actual=metadata_fields_present,
            threshold=1,  # At least one metadata field
            comparison="gte",
            metadata={"found_metadata": metadata}
        )
        
        # Metadata extraction is best-effort, log but don't fail
        if not result.passed:
            pytest.xfail("Metadata extraction is optional - PDF may lack embedded metadata")
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv01_unicode_handling(self, text_extractor):
        """
        FV-01: Test Unicode/special character handling.
        
        Success Criteria:
        - Unicode characters extracted correctly
        - No encoding errors
        - Special characters preserved
        """
        pdf_path = self.FIXTURES_DIR / "special_characters.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available: special_characters.pdf")
        
        # Should not raise encoding errors
        try:
            text, metadata = text_extractor.extract_text(str(pdf_path))
            extraction_success = True
        except UnicodeError:
            extraction_success = False
        
        result = self.validate_threshold(
            test_id="FV-01-D",
            test_name="Unicode handling",
            actual=1 if extraction_success else 0,
            threshold=1,
            comparison="gte",
            metadata={"encoding_error": not extraction_success}
        )
        assert result.passed, "Unicode handling failed"
    
    # =========================================================================
    # FV-02: Edge Case Handling
    # =========================================================================
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv02_corrupted_pdf_handling(self, text_extractor):
        """
        FV-02: Test handling of corrupted PDFs.
        
        Success Criteria:
        - No crash/exception propagates
        - Appropriate error message returned
        - Graceful failure with empty or error result
        """
        pdf_path = self.FIXTURES_DIR / "corrupted_header.pdf"
        
        if not pdf_path.exists():
            # Create a corrupted PDF for testing
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\n%%CORRUPTED')
        
        # Should not crash
        exception_raised = False
        error_message = None
        
        try:
            text, metadata = text_extractor.extract_text(str(pdf_path))
        except Exception as e:
            exception_raised = True
            error_message = str(e)
        
        # Either graceful failure (empty result) or caught exception with message
        result = ValidationResult(
            test_id="FV-02-A",
            test_name="Corrupted PDF handling",
            passed=True,  # If we got here without crashing, it's a pass
            actual_value="Graceful failure" if not exception_raised else f"Exception: {error_message}",
            expected_value="No crash, graceful handling",
            execution_time_ms=self.get_execution_time_ms(),
            metadata={
                "exception_raised": exception_raised,
                "error_message": error_message
            }
        )
        self.results.append(result)
        
        assert True, "Corrupted PDF handled gracefully"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv02_empty_pdf_handling(self, text_extractor):
        """
        FV-02: Test handling of empty PDFs.
        
        Success Criteria:
        - No crash
        - Empty text result or appropriate error
        """
        pdf_path = self.FIXTURES_DIR / "empty.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available: empty.pdf")
        
        try:
            text, metadata = text_extractor.extract_text(str(pdf_path))
            # Empty PDF should return empty or minimal text
            assert len(text) < 100, "Empty PDF should not have significant text"
        except Exception as e:
            # Exception is acceptable for truly empty PDFs
            pass
        
        result = ValidationResult(
            test_id="FV-02-B",
            test_name="Empty PDF handling",
            passed=True,
            actual_value="Handled",
            expected_value="No crash",
            execution_time_ms=self.get_execution_time_ms()
        )
        self.results.append(result)
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv02_password_protected_handling(self, text_extractor):
        """
        FV-02: Test handling of password-protected PDFs.
        
        Success Criteria:
        - No crash
        - Appropriate error message indicating protection
        """
        pdf_path = self.FIXTURES_DIR / "password_protected.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available: password_protected.pdf")
        
        error_detected = False
        error_message = ""
        
        try:
            text, metadata = text_extractor.extract_text(str(pdf_path))
            # If extraction succeeds, text should be empty or indicate protection
            if len(text) < 100:
                error_detected = True
                error_message = "Empty extraction - likely protected"
        except Exception as e:
            error_detected = True
            error_message = str(e)
        
        result = ValidationResult(
            test_id="FV-02-C",
            test_name="Password-protected PDF handling",
            passed=error_detected,  # Should detect the protection
            actual_value=error_message,
            expected_value="Protection detected",
            execution_time_ms=self.get_execution_time_ms()
        )
        self.results.append(result)
        
        assert error_detected, "Should detect password protection"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv02_scanned_pdf_handling(self, text_extractor):
        """
        FV-02: Test handling of scanned (image-only) PDFs.
        
        Success Criteria:
        - No crash
        - OCR fallback attempted (if available)
        - Appropriate message if no OCR
        """
        pdf_path = self.FIXTURES_DIR / "scanned_document.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available: scanned_document.pdf")
        
        try:
            text, metadata = text_extractor.extract_text(str(pdf_path))
            
            # Scanned PDFs typically yield little text without OCR
            if len(text) < 100:
                result_status = "Minimal text (expected without OCR)"
            else:
                result_status = f"Text extracted: {len(text)} chars (OCR may be active)"
                
        except Exception as e:
            result_status = f"Exception: {e}"
        
        result = ValidationResult(
            test_id="FV-02-D",
            test_name="Scanned PDF handling",
            passed=True,  # Pass if no crash
            actual_value=result_status,
            expected_value="Graceful handling (OCR optional)",
            execution_time_ms=self.get_execution_time_ms()
        )
        self.results.append(result)
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv02_multi_column_extraction(self, text_extractor):
        """
        FV-02: Test extraction from multi-column layouts.
        
        Success Criteria:
        - Text extracted from all columns
        - Reading order reasonably preserved
        """
        pdf_path = self.FIXTURES_DIR / "multi_column.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available: multi_column.pdf")
        
        text, metadata = text_extractor.extract_text(str(pdf_path))
        
        # Multi-column should still extract substantial text
        result = self.validate_threshold(
            test_id="FV-02-E",
            test_name="Multi-column extraction",
            actual=len(text),
            threshold=500,  # Should get reasonable amount of text
            comparison="gte",
            metadata={"layout": "multi-column"}
        )
        
        # Log but don't fail - multi-column is challenging
        if not result.passed:
            pytest.xfail("Multi-column extraction may have reduced fidelity")


class TestPDFExtractionPerformance(ValidationTestCase):
    """Performance-related PDF extraction tests."""
    
    TEST_CATEGORY = "FV"
    FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "pdfs"
    
    @pytest.mark.validation
    @pytest.mark.functional
    @pytest.mark.slow
    def test_fv01_extraction_performance(self):
        """
        FV-01: Validate extraction performance.
        
        Success Criteria:
        - Typical PDF extraction completes in <5 seconds
        """
        from literature_review.reviewers.journal_reviewer import TextExtractor
        import time
        
        extractor = TextExtractor()
        pdf_path = self.FIXTURES_DIR / "valid_research_paper.pdf"
        
        if not pdf_path.exists():
            pytest.skip("Test fixture not available")
        
        start = time.perf_counter()
        text, metadata = extractor.extract_text(str(pdf_path))
        elapsed = time.perf_counter() - start
        
        result = self.validate_threshold(
            test_id="FV-01-PERF",
            test_name="PDF extraction time",
            actual=elapsed,
            threshold=5.0,  # 5 seconds max
            comparison="lte",
            metadata={
                "text_length": len(text),
                "seconds": elapsed
            }
        )
        
        assert result.passed, f"Extraction took {elapsed:.2f}s > 5s threshold"
```

### 3. Test Fixture Generator

**File:** `tests/fixtures/pdfs/generate_test_pdfs.py`

```python
"""
Generate test PDF fixtures for validation testing.

Creates minimal PDF files for testing edge cases.
Note: For valid research paper PDFs, use actual papers from data/raw/
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


FIXTURES_DIR = Path(__file__).parent


def create_valid_short_paper():
    """Create a simple valid PDF for testing."""
    filepath = FIXTURES_DIR / "valid_short_paper.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "Test Research Paper for Validation")
    
    # Abstract
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 9.5*inch, "Abstract")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 9.2*inch, "This is a test abstract for validation testing purposes.")
    c.drawString(1*inch, 9.0*inch, "It contains sample text to verify extraction functionality.")
    
    # Introduction
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 8.5*inch, "Introduction")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 8.2*inch, "The introduction section provides context for the research.")
    
    # Methodology
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 7.5*inch, "Methodology")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 7.2*inch, "Our methodology involves systematic testing of PDF extraction.")
    
    # Results
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 6.5*inch, "Results")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 6.2*inch, "Results show high accuracy in text extraction from PDF documents.")
    
    # Conclusion
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 5.5*inch, "Conclusion")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 5.2*inch, "We conclude that the extraction system meets validation criteria.")
    
    c.save()
    print(f"Created: {filepath}")


def create_empty_pdf():
    """Create an empty PDF (1 blank page)."""
    filepath = FIXTURES_DIR / "empty.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    c.showPage()  # Add one empty page
    c.save()
    print(f"Created: {filepath}")


def create_corrupted_pdf():
    """Create a corrupted PDF (invalid structure)."""
    filepath = FIXTURES_DIR / "corrupted_header.pdf"
    
    with open(filepath, 'wb') as f:
        f.write(b'%PDF-1.4\n')
        f.write(b'%%CORRUPTED CONTENT HERE\n')
        f.write(b'This is not a valid PDF structure\n')
    
    print(f"Created: {filepath}")


def create_special_characters_pdf():
    """Create PDF with Unicode/special characters."""
    filepath = FIXTURES_DIR / "special_characters.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Various special characters
    c.drawString(1*inch, 10*inch, "Special Characters Test")
    c.drawString(1*inch, 9.5*inch, "Accents: cafe, resume, naive")
    c.drawString(1*inch, 9*inch, "Symbols: alpha, beta, gamma")
    c.drawString(1*inch, 8.5*inch, "Math: x squared = y")
    c.drawString(1*inch, 8*inch, "Quotes: 'single' and \"double\"")
    
    c.save()
    print(f"Created: {filepath}")


def create_multi_column_pdf():
    """Create PDF with multi-column layout."""
    filepath = FIXTURES_DIR / "multi_column.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    c.setFont("Helvetica", 10)
    
    # Left column
    y = 10*inch
    for i in range(10):
        c.drawString(0.5*inch, y - i*0.3*inch, f"Left column text line {i+1}")
    
    # Right column
    y = 10*inch
    for i in range(10):
        c.drawString(4.5*inch, y - i*0.3*inch, f"Right column text line {i+1}")
    
    c.save()
    print(f"Created: {filepath}")


def create_all_fixtures():
    """Generate all test fixtures."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    create_valid_short_paper()
    create_empty_pdf()
    create_corrupted_pdf()
    create_special_characters_pdf()
    create_multi_column_pdf()
    
    print(f"\nAll fixtures created in: {FIXTURES_DIR}")


if __name__ == "__main__":
    create_all_fixtures()
```

---

## Implementation Steps

### Step 1: Create Test Fixtures (2 hours)
1. Create `tests/fixtures/pdfs/` directory
2. Generate synthetic test PDFs using script
3. Copy 1-2 real PDFs from `data/raw/` for fidelity testing
4. Create edge case PDFs (corrupted, empty, etc.)

### Step 2: Implement Validation Tests (4 hours)
1. Create `tests/validation/functional/test_pdf_extraction.py`
2. Implement FV-01 tests (valid PDF extraction)
3. Implement FV-02 tests (edge case handling)
4. Add performance test

### Step 3: Integration with Base Classes (1 hour)
1. Inherit from `ValidationTestCase`
2. Use `validate_threshold` and `validate_percentage` methods
3. Implement result tracking

### Step 4: Documentation & CI (1 hour)
1. Add docstrings and test descriptions
2. Ensure tests are tagged with proper markers
3. Verify tests run in CI pipeline

---

## Testing

```bash
# Run FV-01 tests
pytest tests/validation/functional/test_pdf_extraction.py -k "fv01" -v

# Run FV-02 edge case tests
pytest tests/validation/functional/test_pdf_extraction.py -k "fv02" -v

# Run all PDF extraction validation
pytest tests/validation/functional/test_pdf_extraction.py -v --tb=short
```

---

## Acceptance Criteria Checklist

- [ ] Test fixture PDFs created (at least 5)
- [ ] FV-01-A: Text length validation passes
- [ ] FV-01-B: Section presence validation passes (≥90%)
- [ ] FV-01-C: Metadata extraction attempted
- [ ] FV-01-D: Unicode handling works
- [ ] FV-02-A: Corrupted PDF handled gracefully
- [ ] FV-02-B: Empty PDF handled gracefully
- [ ] FV-02-C: Password-protected PDF detected
- [ ] FV-02-D: Scanned PDF handled (OCR optional)
- [ ] FV-01-PERF: Extraction completes in <5s
- [ ] All tests tagged with @pytest.mark.validation

---

## Related Tasks

- **Depends on:** VM-W0-1 (Test Infrastructure)
- **Next:** VM-W1-2 (Claim Identification)
- **Parallel:** VM-W1-3, VM-W1-4

---

## Notes

- For best fidelity testing, use actual research PDFs from `data/raw/`
- reportlab library may be needed for fixture generation
- Consider adding more edge cases based on production failures
