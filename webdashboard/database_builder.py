"""
Research Database Builder

Extracts metadata from uploaded PDFs and builds a research database CSV
matching the format expected by the orchestrator.
"""

import csv
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from literature_review.metadata_extractor import EnhancedMetadataExtractor
    ENHANCED_EXTRACTION_AVAILABLE = True
except ImportError:
    ENHANCED_EXTRACTION_AVAILABLE = False

logger = logging.getLogger(__name__)


class ResearchDatabaseBuilder:
    """Builds research database CSV from uploaded PDFs"""
    
    def __init__(self, job_id: str, pdf_files: List[Path], use_enhanced_extraction: bool = True):
        """
        Initialize database builder
        
        Args:
            job_id: Unique job identifier
            pdf_files: List of PDF file paths to process
            use_enhanced_extraction: Use enhanced metadata extraction if available
        """
        self.job_id = job_id
        self.pdf_files = pdf_files
        self.output_dir = Path(f"workspace/jobs/{job_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_enhanced_extraction = use_enhanced_extraction and ENHANCED_EXTRACTION_AVAILABLE
        
        if self.use_enhanced_extraction:
            self.enhanced_extractor = EnhancedMetadataExtractor()
            logger.info("Using enhanced metadata extraction with PyMuPDF")
        else:
            self.enhanced_extractor = None
            logger.info("Using basic metadata extraction with PyPDF2")
    
    def build_database(self) -> Path:
        """
        Extract metadata from PDFs and create research database CSV
        
        Returns:
            Path to created CSV file
        """
        if PyPDF2 is None:
            raise ImportError("PyPDF2 is required for PDF processing. Install with: pip install PyPDF2")
        
        records = []
        
        for pdf_path in self.pdf_files:
            try:
                metadata = self._extract_pdf_metadata(pdf_path)
                records.append(metadata)
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
                # Add placeholder record
                records.append(self._create_placeholder_record(pdf_path))
        
        # Write to CSV
        csv_path = self.output_dir / "research_database.csv"
        self._write_csv(records, csv_path)
        
        return csv_path
    
    def _extract_pdf_metadata(self, pdf_path: Path) -> Dict:
        """Extract metadata from a single PDF"""
        # Use enhanced extraction if available
        if self.use_enhanced_extraction and self.enhanced_extractor:
            try:
                metadata = self.enhanced_extractor.extract_metadata(str(pdf_path))
                
                # Convert to database format
                # Join authors list into comma-separated string
                authors_str = ", ".join(metadata.get('authors', ['Unknown']))
                
                # Use current year as fallback
                year = metadata.get('year') or datetime.now().year
                
                # Log confidence scores for monitoring
                confidence = metadata.get('confidence', {})
                low_confidence = [k for k, v in confidence.items() if v < 0.5]
                if low_confidence:
                    logger.warning(
                        f"Low confidence metadata for {pdf_path.name}: {low_confidence}"
                    )
                
                return {
                    "Title": metadata.get('title', pdf_path.stem),
                    "Authors": authors_str,
                    "Year": year,
                    "File": str(pdf_path),
                    "Abstract": metadata.get('abstract', ''),
                    "Requirement(s)": "[]",  # Empty initially, filled by Judge
                    "Score": "",
                    "Keywords": "",  # Could be extracted from journal field
                    "DOI": metadata.get('doi', ''),  # Add DOI if available
                    "Journal": metadata.get('journal', ''),  # Add journal if available
                }
            except Exception as e:
                logger.error(f"Enhanced extraction failed for {pdf_path}, falling back to basic: {e}")
                # Fall through to basic extraction
        
        # Basic extraction with PyPDF2 (fallback)
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Extract PDF metadata
            info = reader.metadata or {}
            
            # Extract first page text for title extraction
            first_page_text = ""
            if len(reader.pages) > 0:
                first_page_text = reader.pages[0].extract_text()
            
            # Try to extract title
            title = (
                info.get('/Title') or
                self._extract_title_from_text(first_page_text) or
                pdf_path.stem
            )
            
            # Try to extract authors
            authors = (
                info.get('/Author') or
                self._extract_authors_from_text(first_page_text) or
                "Unknown"
            )
            
            # Try to extract year
            year = (
                self._extract_year_from_metadata(info) or
                self._extract_year_from_text(first_page_text) or
                datetime.now().year
            )
            
            return {
                "Title": title,
                "Authors": authors,
                "Year": year,
                "File": str(pdf_path),
                "Abstract": self._extract_abstract(first_page_text),
                "Requirement(s)": "[]",  # Empty initially, filled by Judge
                "Score": "",
                "Keywords": self._extract_keywords(first_page_text)
            }
    
    def _extract_title_from_text(self, text: str) -> str:
        """Attempt to extract title from PDF text"""
        if not text:
            return ""
        
        # Get first few lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Title is usually in first 5 lines, longest line
        candidates = lines[:5]
        if candidates:
            return max(candidates, key=len)[:200]  # Limit length
        
        return ""
    
    def _extract_authors_from_text(self, text: str) -> str:
        """Attempt to extract authors from PDF text"""
        # Look for common author patterns
        # This is heuristic and may need improvement
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            # Look for lines with names (capital letters followed by lowercase)
            if re.match(r'^[A-Z][a-z]+\s+[A-Z]', line):
                return line.strip()[:200]
        
        return "Unknown"
    
    def _extract_year_from_metadata(self, info: Dict) -> Optional[int]:
        """Attempt to extract year from PDF metadata"""
        # Try to get creation date from metadata
        creation_date = info.get('/CreationDate', '')
        if creation_date:
            # PDF date format: D:YYYYMMDDHHmmSS
            match = re.search(r'D:(\d{4})', creation_date)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= datetime.now().year:
                    return year
        
        return None
    
    def _extract_year_from_text(self, text: str) -> Optional[int]:
        """Attempt to extract publication year from text"""
        # Look for 4-digit years between 1900-2099
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        
        if matches:
            # Return most recent plausible year
            years = [int(y) for y in matches if 1900 <= int(y) <= datetime.now().year]
            if years:
                return max(years)
        
        return None
    
    def _extract_abstract(self, text: str) -> str:
        """Attempt to extract abstract"""
        # Look for "Abstract" section
        abstract_match = re.search(
            r'abstract[:\s]+(.*?)(?:\n\n|introduction|keywords)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if abstract_match:
            return abstract_match.group(1).strip()[:500]  # Limit length
        
        return ""
    
    def _extract_keywords(self, text: str) -> str:
        """Attempt to extract keywords"""
        keywords_match = re.search(
            r'keywords[:\s]+(.*?)(?:\n\n|\d+\s+introduction)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if keywords_match:
            return keywords_match.group(1).strip()[:200]
        
        return ""
    
    def _create_placeholder_record(self, pdf_path: Path) -> Dict:
        """Create placeholder record when metadata extraction fails"""
        return {
            "Title": pdf_path.stem,
            "Authors": "Unknown",
            "Year": datetime.now().year,
            "File": str(pdf_path),
            "Abstract": "",
            "Requirement(s)": "[]",
            "Score": "",
            "Keywords": ""
        }
    
    def _write_csv(self, records: List[Dict], output_path: Path):
        """Write records to CSV file"""
        if not records:
            raise ValueError("No records to write")
        
        fieldnames = [
            "Title", "Authors", "Year", "File", "Abstract",
            "Requirement(s)", "Score", "Keywords"
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        logger.info(f"Created research database: {output_path} ({len(records)} records)")
