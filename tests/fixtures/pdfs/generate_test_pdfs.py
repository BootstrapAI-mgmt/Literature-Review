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
    
    # Add PDF metadata
    c.setAuthor("Test Author")
    c.setTitle("Test Research Paper for Validation")
    c.setSubject("PDF Extraction Validation")
    c.setCreator("Literature Review Test Suite")
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "Test Research Paper for Validation")
    
    # Abstract
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 9.5*inch, "Abstract")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 9.2*inch, "This is a test abstract for validation testing purposes.")
    c.drawString(1*inch, 9.0*inch, "It contains sample text to verify extraction functionality.")
    c.drawString(1*inch, 8.8*inch, "The extraction system should identify this section correctly.")
    
    # Introduction
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 8.3*inch, "1. Introduction")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 8.0*inch, "The introduction section provides context for the research.")
    c.drawString(1*inch, 7.8*inch, "This paper presents a comprehensive analysis of the topic.")
    c.drawString(1*inch, 7.6*inch, "We explore various aspects of machine learning and neural networks.")
    
    # Methodology
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 7.1*inch, "2. Methodology")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 6.8*inch, "Our methodology involves systematic testing of PDF extraction.")
    c.drawString(1*inch, 6.6*inch, "We employ multiple extraction methods including pypdf and pdfplumber.")
    c.drawString(1*inch, 6.4*inch, "The approach ensures high fidelity text extraction from documents.")
    
    # Results
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 5.9*inch, "3. Results")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 5.6*inch, "Results show high accuracy in text extraction from PDF documents.")
    c.drawString(1*inch, 5.4*inch, "The system achieved over 90% fidelity in our benchmark tests.")
    c.drawString(1*inch, 5.2*inch, "Table 1 shows the comparison of different extraction methods.")
    
    # Conclusion
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 4.7*inch, "4. Conclusion")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 4.4*inch, "We conclude that the extraction system meets validation criteria.")
    c.drawString(1*inch, 4.2*inch, "Future work will focus on improving OCR capabilities.")
    
    # References
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 3.7*inch, "References")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 3.4*inch, "[1] Smith, J. (2023). PDF Extraction Methods. Journal of Text Mining.")
    c.drawString(1*inch, 3.2*inch, "[2] Jones, A. (2024). Neural Network Text Processing. AI Review.")
    
    c.save()
    print(f"Created: {filepath}")
    return filepath


def create_valid_research_paper():
    """Create a more substantial valid PDF for fidelity testing."""
    filepath = FIXTURES_DIR / "valid_research_paper.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    
    # Add PDF metadata
    c.setAuthor("Research Author, PhD")
    c.setTitle("Comprehensive Analysis of Text Extraction Methods")
    c.setSubject("Computer Science - Natural Language Processing")
    c.setCreator("Literature Review Test Suite")
    
    # Page 1: Title and Abstract
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(4.25*inch, 10*inch, "Comprehensive Analysis of")
    c.drawCentredString(4.25*inch, 9.6*inch, "Text Extraction Methods")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(4.25*inch, 9*inch, "Research Author, PhD")
    c.drawCentredString(4.25*inch, 8.7*inch, "University of Testing")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 8*inch, "Abstract")
    c.setFont("Helvetica", 10)
    
    abstract_text = [
        "This paper presents a comprehensive analysis of text extraction methods for",
        "PDF documents. We evaluate multiple approaches including pypdf, pdfplumber,",
        "and optical character recognition (OCR) techniques. Our findings demonstrate",
        "that hybrid extraction methods achieve the highest fidelity rates, with",
        "accuracy exceeding 95% for standard documents. The implications of this",
        "research extend to automated document processing pipelines and literature",
        "review systems. We provide benchmarks and recommendations for optimal",
        "extraction configurations based on document type and quality."
    ]
    
    y_pos = 7.7
    for line in abstract_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.25
    
    # Keywords
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, 5.5*inch, "Keywords:")
    c.setFont("Helvetica", 10)
    c.drawString(2*inch, 5.5*inch, "PDF extraction, text mining, OCR, document processing, NLP")
    
    # Introduction
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 5*inch, "1. Introduction")
    c.setFont("Helvetica", 10)
    
    intro_text = [
        "Text extraction from PDF documents is a fundamental task in many automated",
        "systems, including literature review pipelines, document management systems,",
        "and data mining applications. The quality of extracted text directly impacts",
        "downstream natural language processing tasks such as named entity recognition,",
        "summarization, and question answering.",
        "",
        "PDF documents present unique challenges for text extraction due to their",
        "complex structure. Unlike plain text or HTML documents, PDFs encode text as",
        "positioned glyphs rather than semantic content. This encoding can lead to",
        "issues with reading order, column detection, and special character handling."
    ]
    
    y_pos = 4.7
    for line in intro_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.25
    
    c.showPage()  # Page 2
    
    # Methodology
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 10*inch, "2. Methodology")
    c.setFont("Helvetica", 10)
    
    method_text = [
        "We evaluate three primary extraction methods in our study:",
        "",
        "2.1 pypdf Library",
        "The pypdf library provides pure Python PDF parsing capabilities. It extracts",
        "text by interpreating the PDF content stream and combining text fragments.",
        "",
        "2.2 pdfplumber Library",
        "pdfplumber offers more sophisticated extraction with better handling of",
        "complex layouts, tables, and multi-column documents.",
        "",
        "2.3 OCR Fallback",
        "For scanned documents, we employ optical character recognition using",
        "industry-standard OCR engines to convert images to text."
    ]
    
    y_pos = 9.7
    for line in method_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.25
    
    # Results
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 6*inch, "3. Results")
    c.setFont("Helvetica", 10)
    
    results_text = [
        "Our experimental results demonstrate significant variation in extraction",
        "quality based on document characteristics and extraction method.",
        "",
        "For standard research papers with single-column layouts, both pypdf and",
        "pdfplumber achieved accuracy rates above 95%. pdfplumber showed superior",
        "performance on multi-column documents and tables.",
        "",
        "Table 1 presents the comparison of extraction methods across document types.",
        "The hybrid approach combining multiple extractors yielded the best overall",
        "results with a mean accuracy of 97.3%."
    ]
    
    y_pos = 5.7
    for line in results_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.25
    
    c.showPage()  # Page 3
    
    # Discussion and Conclusion
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 10*inch, "4. Discussion")
    c.setFont("Helvetica", 10)
    
    discussion_text = [
        "The results confirm that no single extraction method is optimal for all",
        "document types. Complex layouts require sophisticated approaches such as",
        "pdfplumber, while simpler documents can be efficiently processed with pypdf.",
        "",
        "A key finding is the importance of extraction quality validation. Without",
        "quality checks, downstream systems may process corrupted or incomplete text."
    ]
    
    y_pos = 9.7
    for line in discussion_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.25
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 7.5*inch, "5. Conclusion")
    c.setFont("Helvetica", 10)
    
    conclusion_text = [
        "This paper has demonstrated that effective PDF text extraction requires a",
        "multi-method approach with quality validation. Our recommendations include:",
        "",
        "1. Use pdfplumber for complex layouts and tables",
        "2. Implement OCR fallback for scanned documents",
        "3. Validate extraction quality before downstream processing",
        "4. Handle edge cases gracefully with appropriate error messages"
    ]
    
    y_pos = 7.2
    for line in conclusion_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.25
    
    # References
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, 5*inch, "References")
    c.setFont("Helvetica", 10)
    
    references_text = [
        "[1] Smith, J., & Jones, A. (2023). PDF Extraction Methods: A Survey.",
        "    Journal of Text Mining, 15(2), 45-67.",
        "",
        "[2] Brown, M. (2024). Neural Network Approaches to Document Processing.",
        "    AI Review, 8(1), 112-128.",
        "",
        "[3] Wilson, K., et al. (2023). Benchmark Dataset for PDF Extraction.",
        "    Proceedings of the Conference on NLP, 234-245.",
        "",
        "[4] Garcia, L. (2022). OCR Technologies: Current State and Future.",
        "    Computer Vision Journal, 22(4), 78-95."
    ]
    
    y_pos = 4.7
    for line in references_text:
        c.drawString(1*inch, y_pos*inch, line)
        y_pos -= 0.2
    
    c.save()
    print(f"Created: {filepath}")
    return filepath


def create_empty_pdf():
    """Create an empty PDF (1 blank page)."""
    filepath = FIXTURES_DIR / "empty.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    c.showPage()  # Add one empty page
    c.save()
    print(f"Created: {filepath}")
    return filepath


def create_corrupted_pdf():
    """Create a corrupted PDF (invalid structure)."""
    filepath = FIXTURES_DIR / "corrupted_header.pdf"
    
    with open(filepath, 'wb') as f:
        f.write(b'%PDF-1.4\n')
        f.write(b'%%CORRUPTED CONTENT HERE\n')
        f.write(b'This is not a valid PDF structure\n')
        f.write(b'Random bytes follow: ')
        f.write(bytes(range(256)))
    
    print(f"Created: {filepath}")
    return filepath


def create_truncated_pdf():
    """Create a truncated PDF (starts valid but cut off)."""
    filepath = FIXTURES_DIR / "truncated.pdf"
    
    # Create a valid PDF first
    temp_path = FIXTURES_DIR / "temp_for_truncate.pdf"
    c = canvas.Canvas(str(temp_path), pagesize=letter)
    c.drawString(1*inch, 10*inch, "This PDF will be truncated")
    c.save()
    
    # Read and truncate
    with open(temp_path, 'rb') as f:
        content = f.read()
    
    # Truncate to 50% of original size
    truncated_content = content[:len(content)//2]
    
    with open(filepath, 'wb') as f:
        f.write(truncated_content)
    
    # Clean up temp file
    os.remove(temp_path)
    
    print(f"Created: {filepath}")
    return filepath


def create_special_characters_pdf():
    """Create PDF with Unicode/special characters."""
    filepath = FIXTURES_DIR / "special_characters.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Title
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, 10*inch, "Special Characters Test Document")
    
    c.setFont("Helvetica", 10)
    # Note: reportlab has limited Unicode support with default fonts,
    # so we use ASCII-safe representations of concepts
    c.drawString(1*inch, 9.5*inch, "Section 1: Accented Characters")
    c.drawString(1*inch, 9.2*inch, "cafe, resume, naive, fiancee, cliche")
    
    c.drawString(1*inch, 8.7*inch, "Section 2: Greek Letter Names")  
    c.drawString(1*inch, 8.4*inch, "alpha, beta, gamma, delta, epsilon, pi, sigma")
    
    c.drawString(1*inch, 7.9*inch, "Section 3: Mathematical Expressions")
    c.drawString(1*inch, 7.6*inch, "x^2 + y^2 = z^2 (Pythagorean theorem)")
    c.drawString(1*inch, 7.3*inch, "E = mc^2 (Energy equation)")
    c.drawString(1*inch, 7.0*inch, "sum(i=1 to n) = n(n+1)/2")
    
    c.drawString(1*inch, 6.5*inch, "Section 4: Quotation Styles")
    c.drawString(1*inch, 6.2*inch, "'Single quotes' and \"double quotes\"")
    c.drawString(1*inch, 5.9*inch, "En-dash: 1990-2000, Em-dash: word--word")
    
    c.drawString(1*inch, 5.4*inch, "Section 5: Symbols and Punctuation")
    c.drawString(1*inch, 5.1*inch, "& (ampersand), @ (at), # (hash), $ (dollar)")
    c.drawString(1*inch, 4.8*inch, "% (percent), * (asterisk), + (plus), = (equals)")
    
    c.save()
    print(f"Created: {filepath}")
    return filepath


def create_multi_column_pdf():
    """Create PDF with multi-column layout."""
    filepath = FIXTURES_DIR / "multi_column.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    
    # Title spanning both columns
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(4.25*inch, 10.5*inch, "Multi-Column Layout Test Document")
    
    c.setFont("Helvetica", 9)
    
    # Left column content
    left_x = 0.75*inch
    left_text = [
        "LEFT COLUMN TEXT",
        "",
        "This is the left column of",
        "a two-column layout. The",
        "extraction system should",
        "be able to identify and",
        "correctly order text from",
        "multi-column documents.",
        "",
        "Column detection is one of",
        "the challenges in PDF text",
        "extraction. Without proper",
        "handling, text from both",
        "columns may be interleaved",
        "incorrectly.",
        "",
        "The left column continues",
        "with additional content to",
        "provide more test data for",
        "validation purposes."
    ]
    
    y = 10*inch
    for line in left_text:
        c.drawString(left_x, y, line)
        y -= 0.25*inch
    
    # Right column content
    right_x = 4.25*inch
    right_text = [
        "RIGHT COLUMN TEXT",
        "",
        "This is the right column",
        "of the same document. It",
        "runs parallel to the left",
        "column and contains its",
        "own distinct content.",
        "",
        "Multi-column layouts are",
        "common in academic papers",
        "and research journals. A",
        "robust extraction system",
        "must handle these layouts",
        "gracefully.",
        "",
        "The right column also has",
        "additional lines of text",
        "to ensure comprehensive",
        "testing of the extractor."
    ]
    
    y = 10*inch
    for line in right_text:
        c.drawString(right_x, y, line)
        y -= 0.25*inch
    
    c.save()
    print(f"Created: {filepath}")
    return filepath


def create_tables_heavy_pdf():
    """Create PDF with table-like structures."""
    filepath = FIXTURES_DIR / "tables_heavy.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, 10.5*inch, "Tables Heavy Document")
    
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 10*inch, "This document contains tabular data for extraction testing.")
    
    # Table 1
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 9.5*inch, "Table 1: Extraction Method Comparison")
    
    c.setFont("Helvetica", 9)
    # Header row
    c.drawString(1*inch, 9.2*inch, "Method")
    c.drawString(2.5*inch, 9.2*inch, "Accuracy")
    c.drawString(4*inch, 9.2*inch, "Speed")
    c.drawString(5.5*inch, 9.2*inch, "Memory")
    
    # Data rows
    rows = [
        ("pypdf", "92%", "Fast", "Low"),
        ("pdfplumber", "95%", "Medium", "Medium"),
        ("OCR", "88%", "Slow", "High"),
        ("Hybrid", "97%", "Variable", "Variable"),
    ]
    
    y = 8.9*inch
    for row in rows:
        c.drawString(1*inch, y, row[0])
        c.drawString(2.5*inch, y, row[1])
        c.drawString(4*inch, y, row[2])
        c.drawString(5.5*inch, y, row[3])
        y -= 0.25*inch
    
    # Table 2
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, 7.5*inch, "Table 2: Document Type Results")
    
    c.setFont("Helvetica", 9)
    # Header
    c.drawString(1*inch, 7.2*inch, "Document Type")
    c.drawString(3*inch, 7.2*inch, "Success Rate")
    c.drawString(5*inch, 7.2*inch, "Notes")
    
    rows2 = [
        ("Standard Paper", "98%", "Excellent"),
        ("Multi-column", "91%", "Good"),
        ("Scanned", "85%", "OCR needed"),
        ("Tables Heavy", "89%", "Complex layout"),
        ("Image-based", "70%", "Limited"),
    ]
    
    y = 6.9*inch
    for row in rows2:
        c.drawString(1*inch, y, row[0])
        c.drawString(3*inch, y, row[1])
        c.drawString(5*inch, y, row[2])
        y -= 0.25*inch
    
    c.save()
    print(f"Created: {filepath}")
    return filepath


def create_all_fixtures():
    """Generate all test fixtures."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    created_files.append(create_valid_short_paper())
    created_files.append(create_valid_research_paper())
    created_files.append(create_empty_pdf())
    created_files.append(create_corrupted_pdf())
    created_files.append(create_truncated_pdf())
    created_files.append(create_special_characters_pdf())
    created_files.append(create_multi_column_pdf())
    created_files.append(create_tables_heavy_pdf())
    
    print(f"\nAll {len(created_files)} fixtures created in: {FIXTURES_DIR}")
    return created_files


if __name__ == "__main__":
    create_all_fixtures()
