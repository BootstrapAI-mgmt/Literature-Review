"""
Document Parser
Parses Markdown documents for validation content extraction.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class MarkdownParser:
    """Parses Markdown documents for structure and content extraction"""
    
    def __init__(self, path: Path):
        self.path = Path(path)
        self._content: Optional[str] = None
        self._lines: Optional[List[str]] = None
    
    def load(self) -> str:
        """Load the markdown file content"""
        if self._content is not None:
            return self._content
        
        if not self.path.exists():
            raise FileNotFoundError(f"Document not found: {self.path}")
        
        with open(self.path, 'r', encoding='utf-8') as f:
            self._content = f.read()
            self._lines = self._content.splitlines()
        
        return self._content
    
    @property
    def lines(self) -> List[str]:
        if self._lines is None:
            self.load()
        return self._lines or []
    
    def extract_sections(self) -> Dict[str, str]:
        """Extract all sections (headers) and their content"""
        content = self.load()
        sections = {}
        current_section = None
        current_content = []
        
        for line in self.lines:
            # Match headers (## or ###)
            header_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = header_match.group(2).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def extract_tables(self) -> List[Dict[str, List[str]]]:
        """Extract all markdown tables as list of dicts"""
        content = self.load()
        tables = []
        current_table = None
        headers = []
        
        for line in self.lines:
            # Table row
            if '|' in line and not line.strip().startswith('```'):
                cells = [c.strip() for c in line.split('|')[1:-1]]
                
                # Skip separator row
                if all(re.match(r'^[-:]+$', c) for c in cells):
                    continue
                
                if current_table is None:
                    # This is the header row
                    headers = cells
                    current_table = {h: [] for h in headers}
                else:
                    # Data row
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            current_table[headers[i]].append(cell)
            else:
                # End of table
                if current_table:
                    tables.append(current_table)
                    current_table = None
                    headers = []
        
        # Don't forget last table
        if current_table:
            tables.append(current_table)
        
        return tables
    
    def extract_code_blocks(self) -> List[Tuple[str, str]]:
        """Extract code blocks with their language"""
        content = self.load()
        blocks = []
        in_block = False
        current_lang = ""
        current_content = []
        
        for line in self.lines:
            if line.startswith('```'):
                if in_block:
                    # End of block
                    blocks.append((current_lang, '\n'.join(current_content)))
                    current_content = []
                    in_block = False
                else:
                    # Start of block
                    current_lang = line[3:].strip()
                    in_block = True
            elif in_block:
                current_content.append(line)
        
        return blocks
    
    def find_status_pattern(self, pattern: str) -> Optional[str]:
        """Find a status pattern like '✅ Complete' or '📋 Planned'"""
        content = self.load()
        match = re.search(pattern, content)
        if match:
            return match.group(0)
        return None
    
    def section_exists(self, section_name: str) -> bool:
        """Check if a section header exists"""
        sections = self.extract_sections()
        return section_name in sections or any(
            section_name.lower() in s.lower() for s in sections.keys()
        )
    
    def get_timestamp(self) -> Optional[str]:
        """Extract document timestamp/update date"""
        content = self.load()
        patterns = [
            r'\*\*Updated:\*\*\s*(.+)',
            r'\*\*Last Updated:\*\*\s*(.+)',
            r'Updated:\s*(.+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        return None


def extract_sections(path: Path) -> Dict[str, str]:
    """Convenience function to extract sections from a markdown file"""
    parser = MarkdownParser(path)
    return parser.extract_sections()


def extract_tables(path: Path) -> List[Dict[str, List[str]]]:
    """Convenience function to extract tables from a markdown file"""
    parser = MarkdownParser(path)
    return parser.extract_tables()
