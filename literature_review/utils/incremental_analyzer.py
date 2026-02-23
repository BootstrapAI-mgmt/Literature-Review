"""
Incremental Analysis Support
Track paper fingerprints and detect changes for efficient incremental updates.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)

# Must match SUPPORTED_EXTENSIONS in journal_reviewer.py and deep_reviewer.py
SUPPORTED_EXTENSIONS = ('.pdf', '.html', '.txt', '.json')


class IncrementalAnalyzer:
    """Manage incremental analysis state."""
    
    def __init__(self, state_file: str = 'analysis_cache/incremental_state.json'):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load incremental analysis state."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        
        return {
            'version': '1.0',
            'last_run': None,
            'pillar_hash': None,
            'paper_fingerprints': {},
            'analysis_results': {}
        }
    
    def _save_state(self):
        """Save incremental analysis state."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file."""
        hasher = hashlib.md5()
        
        with open(filepath, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _find_papers(self, paper_dir: str) -> Dict[str, str]:
        """Find all supported paper files recursively and compute hashes."""
        papers = {}
        if os.path.exists(paper_dir):
            for root, dirs, files in os.walk(paper_dir):
                for filename in files:
                    if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                        filepath = os.path.join(root, filename)
                        rel_path = os.path.relpath(filepath, paper_dir)
                        papers[rel_path] = self._calculate_file_hash(filepath)
        return papers
    
    def _calculate_pillar_hash(self, pillar_file: str = 'pillar_definitions.json') -> str:
        """Calculate hash of pillar definitions."""
        if not os.path.exists(pillar_file):
            return 'no-pillars'
        
        with open(pillar_file, 'r') as f:
            pillar_data = json.load(f)
        
        # Hash the JSON structure (sorted for consistency)
        pillar_str = json.dumps(pillar_data, sort_keys=True)
        return hashlib.md5(pillar_str.encode()).hexdigest()
    
    def detect_changes(self, paper_dir: str, pillar_file: str = 'pillar_definitions.json',
                      force: bool = False) -> Dict[str, List[str]]:
        """
        Detect which papers need analysis.
        
        Args:
            paper_dir: Directory containing papers (JSON files)
            pillar_file: Path to pillar definitions
            force: Force re-analysis of all papers
        
        Returns:
            Dictionary with 'new', 'modified', 'unchanged', and 'removed' papers
        """
        logger.info("Detecting changes in papers...")
        
        # Check if pillar definitions changed
        current_pillar_hash = self._calculate_pillar_hash(pillar_file)
        pillar_changed = (current_pillar_hash != self.state.get('pillar_hash'))
        
        if pillar_changed:
            logger.warning("⚠️ Pillar definitions changed - all papers need re-analysis")
        
        if force:
            logger.warning("⚠️ Force flag set - re-analyzing all papers")
        
        # Find all current papers (recursive, all supported extensions)
        current_papers = self._find_papers(paper_dir)
        
        # Compare with previous state
        previous_papers = self.state.get('paper_fingerprints', {})
        
        # Load review_log to identify already-analyzed papers
        # This handles migration from .json-only detection to PDF detection
        reviewed_filenames = set()
        review_log_path = os.path.join(os.path.dirname(paper_dir) if paper_dir != '.' else '.', 'review_log.json')
        if not os.path.exists(review_log_path):
            review_log_path = 'review_log.json'
        if os.path.exists(review_log_path):
            try:
                with open(review_log_path, 'r', encoding='utf-8') as f:
                    review_log = json.load(f)
                if isinstance(review_log, list):
                    reviewed_filenames = set(review_log)
                elif isinstance(review_log, dict):
                    reviewed_filenames = set(review_log.keys())
                logger.info(f"Loaded review log with {len(reviewed_filenames)} entries")
            except Exception as e:
                logger.warning(f"Could not load review log: {e}")
        
        # Also check the database CSV for FILENAME column (catches papers
        # that were analyzed but not recorded in review_log)
        import csv
        import glob
        for csv_path in glob.glob('*database*.csv'):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    if 'FILENAME' in (reader.fieldnames or []):
                        for row in reader:
                            fn = row.get('FILENAME', '').strip()
                            if fn:
                                reviewed_filenames.add(fn)
                logger.info(f"After loading {csv_path}: {len(reviewed_filenames)} total reviewed filenames")
            except Exception as e:
                logger.warning(f"Could not load database CSV {csv_path}: {e}")
        
        new_papers = []
        modified_papers = []
        unchanged_papers = []
        removed_papers = []
        seeded_fingerprints = 0
        
        # Check each current paper
        for rel_path, current_hash in current_papers.items():
            basename = os.path.basename(rel_path)
            if rel_path in previous_papers:
                # Known file — check if modified
                if current_hash != previous_papers[rel_path]:
                    modified_papers.append(rel_path)
                elif pillar_changed or force:
                    modified_papers.append(rel_path)
                else:
                    unchanged_papers.append(rel_path)
            elif basename in reviewed_filenames:
                # Already reviewed but not yet fingerprinted (migration)
                unchanged_papers.append(rel_path)
                # Seed the fingerprint for future runs
                previous_papers[rel_path] = current_hash
                seeded_fingerprints += 1
            else:
                new_papers.append(rel_path)
        
        # Persist any seeded fingerprints
        if seeded_fingerprints > 0:
            self.state['paper_fingerprints'] = previous_papers
            self._save_state()
            logger.info(f"Seeded {seeded_fingerprints} fingerprints from review log (migration)")
        
        # Find removed papers
        for filename in previous_papers:
            if filename not in current_papers:
                removed_papers.append(filename)
        
        changes = {
            'new': sorted(new_papers),
            'modified': sorted(modified_papers),
            'unchanged': sorted(unchanged_papers),
            'removed': sorted(removed_papers)
        }
        
        # Log summary
        logger.info(f"Change detection complete:")
        logger.info(f"  New: {len(new_papers)}")
        logger.info(f"  Modified: {len(modified_papers)}")
        logger.info(f"  Unchanged: {len(unchanged_papers)}")
        logger.info(f"  Removed: {len(removed_papers)}")
        
        return changes
    
    def get_cached_analysis(self, paper_filename: str, stage: str) -> Optional[Dict]:
        """
        Get cached analysis result for a paper.
        
        Args:
            paper_filename: Name of paper file
            stage: Analysis stage (journal_review, judge_analysis, etc.)
        
        Returns:
            Cached analysis result or None if not available
        """
        if paper_filename not in self.state['analysis_results']:
            return None
        
        paper_cache = self.state['analysis_results'][paper_filename]
        return paper_cache.get(stage)
    
    def save_analysis(self, paper_filename: str, stage: str, result: Dict):
        """
        Save analysis result to cache.
        
        Args:
            paper_filename: Name of paper file
            stage: Analysis stage
            result: Analysis result to cache
        """
        if paper_filename not in self.state['analysis_results']:
            self.state['analysis_results'][paper_filename] = {}
        
        self.state['analysis_results'][paper_filename][stage] = result
        self._save_state()
    
    def update_fingerprints(self, paper_dir: str, pillar_file: str = 'pillar_definitions.json'):
        """
        Update file fingerprints after successful analysis.
        
        Args:
            paper_dir: Directory containing papers
            pillar_file: Path to pillar definitions
        """
        logger.info("Updating incremental state...")
        
        # Update pillar hash
        self.state['pillar_hash'] = self._calculate_pillar_hash(pillar_file)
        
        # Update paper fingerprints (recursive, all supported extensions)
        new_fingerprints = self._find_papers(paper_dir)
        
        self.state['paper_fingerprints'] = new_fingerprints
        self.state['last_run'] = datetime.now().isoformat()
        
        # Remove analysis cache for deleted papers
        for filename in list(self.state['analysis_results'].keys()):
            if filename not in new_fingerprints:
                del self.state['analysis_results'][filename]
                logger.debug(f"Removed cache for deleted paper: {filename}")
        
        self._save_state()
        logger.info("Incremental state updated successfully")
    
    def clear_cache(self, paper_filename: Optional[str] = None):
        """
        Clear analysis cache.
        
        Args:
            paper_filename: Clear cache for specific paper (or all if None)
        """
        if paper_filename:
            if paper_filename in self.state['analysis_results']:
                del self.state['analysis_results'][paper_filename]
                logger.info(f"Cleared cache for {paper_filename}")
        else:
            self.state['analysis_results'] = {}
            logger.info("Cleared all analysis cache")
        
        self._save_state()
    
    def get_stats(self) -> Dict:
        """Get incremental analysis statistics."""
        return {
            'last_run': self.state.get('last_run'),
            'total_papers_cached': len(self.state['paper_fingerprints']),
            'papers_with_analysis': len(self.state['analysis_results']),
            'cache_file': self.state_file,
            'pillar_hash': self.state.get('pillar_hash', 'not-set')
        }


# Singleton instance
_incremental_analyzer = None


def get_incremental_analyzer() -> IncrementalAnalyzer:
    """Get global incremental analyzer instance."""
    global _incremental_analyzer
    if _incremental_analyzer is None:
        _incremental_analyzer = IncrementalAnalyzer()
    return _incremental_analyzer
