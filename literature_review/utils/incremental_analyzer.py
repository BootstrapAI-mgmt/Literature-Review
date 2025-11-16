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
        
        # Find all current papers
        current_papers = {}
        if os.path.exists(paper_dir):
            for filename in os.listdir(paper_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(paper_dir, filename)
                    file_hash = self._calculate_file_hash(filepath)
                    current_papers[filename] = file_hash
        
        # Compare with previous state
        previous_papers = self.state.get('paper_fingerprints', {})
        
        new_papers = []
        modified_papers = []
        unchanged_papers = []
        removed_papers = []
        
        # Check each current paper
        for filename, current_hash in current_papers.items():
            if filename not in previous_papers:
                new_papers.append(filename)
            elif current_hash != previous_papers[filename]:
                modified_papers.append(filename)
            elif pillar_changed or force:
                modified_papers.append(filename)  # Treat as modified
            else:
                unchanged_papers.append(filename)
        
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
        
        # Update paper fingerprints
        new_fingerprints = {}
        if os.path.exists(paper_dir):
            for filename in os.listdir(paper_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(paper_dir, filename)
                    new_fingerprints[filename] = self._calculate_file_hash(filepath)
        
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
