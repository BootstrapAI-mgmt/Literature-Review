"""
Duplicate Detection Utilities

Provides functionality to detect duplicate PDFs across upload batches using:
- PDF hash (SHA256)
- Exact title matching
- Fuzzy title matching
"""

import hashlib
import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def compute_pdf_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of PDF file content
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        SHA256 hash as hexadecimal string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_for_duplicates(
    new_papers: List[Dict],
    existing_database: List[Dict],
    fuzzy_threshold: float = 0.95
) -> Dict:
    """
    Check if new papers already exist in database
    
    Duplicate detection methods (in priority order):
    1. Hash match (most reliable - exact file content)
    2. Exact title match (case-insensitive)
    3. Fuzzy title match (>= fuzzy_threshold similarity)
    
    Args:
        new_papers: List of new paper metadata dicts with 'file_path' and 'title'
        existing_database: List of existing paper metadata dicts
        fuzzy_threshold: Minimum similarity ratio for fuzzy matching (0.0-1.0)
    
    Returns:
        dict with keys:
            - 'duplicates': List of duplicate papers
            - 'new': List of truly new papers
            - 'matches': Dict mapping new_paper_id -> existing_paper info
    """
    duplicates = []
    new = []
    matches = {}
    
    # Build lookup structures for existing papers
    existing_hashes = {}
    existing_titles = {}
    
    for paper in existing_database:
        # Build hash lookup if hash exists
        if 'hash' in paper and paper['hash']:
            existing_hashes[paper['hash']] = paper
        
        # Build title lookup
        if 'title' in paper and paper['title']:
            title_key = paper['title'].lower().strip()
            existing_titles[title_key] = paper
    
    # Check each new paper
    for paper in new_papers:
        is_duplicate = False
        match_info = None
        
        # Method 1: Hash match (most reliable)
        if 'file_path' in paper:
            try:
                paper_hash = compute_pdf_hash(Path(paper['file_path']))
                paper['hash'] = paper_hash
                
                if paper_hash in existing_hashes:
                    is_duplicate = True
                    match_info = {
                        'method': 'hash',
                        'existing_paper': existing_hashes[paper_hash],
                        'confidence': 1.0
                    }
            except Exception as e:
                logger.warning(f"Failed to compute hash for {paper.get('original_name', 'unknown')}: {e}")
        
        # Method 2: Exact title match
        if not is_duplicate and 'title' in paper and paper['title']:
            title_key = paper['title'].lower().strip()
            if title_key in existing_titles:
                is_duplicate = True
                match_info = {
                    'method': 'exact_title',
                    'existing_paper': existing_titles[title_key],
                    'confidence': 1.0
                }
        
        # Method 3: Fuzzy title match
        if not is_duplicate and 'title' in paper and paper['title']:
            new_title = paper['title'].lower().strip()
            best_similarity = 0.0
            best_match = None
            
            for existing_title_key, existing_paper in existing_titles.items():
                similarity = SequenceMatcher(None, new_title, existing_title_key).ratio()
                if similarity >= fuzzy_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = existing_paper
            
            if best_match:
                is_duplicate = True
                match_info = {
                    'method': 'fuzzy_title',
                    'existing_paper': best_match,
                    'confidence': best_similarity
                }
        
        # Categorize paper
        if is_duplicate and match_info:
            paper['match_info'] = match_info
            duplicates.append(paper)
            matches[paper.get('original_name', paper.get('id', ''))] = match_info
        else:
            new.append(paper)
    
    return {
        'duplicates': duplicates,
        'new': new,
        'matches': matches
    }


def load_existing_papers_from_review_log(review_log_path: Path) -> List[Dict]:
    """
    Load existing papers from review_log.json
    
    Args:
        review_log_path: Path to review_log.json file
    
    Returns:
        List of paper metadata dictionaries
    """
    import json
    
    if not review_log_path.exists():
        return []
    
    try:
        with open(review_log_path, 'r') as f:
            data = json.load(f)
            
            # Handle both list format and dict format
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'papers' in data:
                return data['papers']
            else:
                logger.warning(f"Unexpected review_log format: {type(data)}")
                return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse review_log.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to load review_log.json: {e}")
        return []
