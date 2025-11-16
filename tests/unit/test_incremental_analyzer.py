"""
Unit tests for IncrementalAnalyzer class.

Tests cover:
- File hash calculation
- Change detection logic
- Pillar hash tracking
- Analysis caching
- State persistence
- Clear cache functionality
"""

import pytest
import tempfile
import os
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.incremental_analyzer import IncrementalAnalyzer


class TestIncrementalAnalyzer:
    """Test suite for IncrementalAnalyzer class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def analyzer(self, temp_dir):
        """Create IncrementalAnalyzer with temp state file."""
        state_file = os.path.join(temp_dir, 'test_state.json')
        return IncrementalAnalyzer(state_file=state_file)
    
    def test_file_hash_calculation(self, analyzer, temp_dir):
        """Test file hash is consistent."""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        hash1 = analyzer._calculate_file_hash(test_file)
        hash2 = analyzer._calculate_file_hash(test_file)
        
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hash length
    
    def test_file_hash_changes_with_content(self, analyzer, temp_dir):
        """Test that hash changes when file content changes."""
        test_file = os.path.join(temp_dir, "test.txt")
        
        with open(test_file, 'w') as f:
            f.write("content 1")
        hash1 = analyzer._calculate_file_hash(test_file)
        
        with open(test_file, 'w') as f:
            f.write("content 2")
        hash2 = analyzer._calculate_file_hash(test_file)
        
        assert hash1 != hash2
    
    def test_pillar_hash_calculation(self, analyzer, temp_dir):
        """Test pillar hash calculation."""
        pillar_file = os.path.join(temp_dir, "pillars.json")
        pillar_data = {"pillar1": {"key": "value"}}
        
        with open(pillar_file, 'w') as f:
            json.dump(pillar_data, f)
        
        hash1 = analyzer._calculate_pillar_hash(pillar_file)
        hash2 = analyzer._calculate_pillar_hash(pillar_file)
        
        assert hash1 == hash2
        assert isinstance(hash1, str)
    
    def test_pillar_hash_no_file(self, analyzer):
        """Test pillar hash when file doesn't exist."""
        hash_val = analyzer._calculate_pillar_hash("nonexistent.json")
        assert hash_val == "no-pillars"
    
    def test_change_detection_all_new(self, analyzer, temp_dir):
        """Test change detection with all new papers."""
        # Create test papers
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        for i in range(3):
            with open(os.path.join(paper_dir, f"paper{i}.json"), 'w') as f:
                json.dump({"title": f"Paper {i}"}, f)
        
        # First run - all new
        changes = analyzer.detect_changes(paper_dir)
        
        assert len(changes['new']) == 3
        assert len(changes['modified']) == 0
        assert len(changes['unchanged']) == 0
        assert len(changes['removed']) == 0
    
    def test_change_detection_no_changes(self, analyzer, temp_dir):
        """Test change detection with no changes."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        # Create test paper
        paper_file = os.path.join(paper_dir, "paper1.json")
        with open(paper_file, 'w') as f:
            json.dump({"title": "Test Paper 1"}, f)
        
        # First run - all new
        changes1 = analyzer.detect_changes(paper_dir)
        assert len(changes1['new']) == 1
        
        # Update fingerprints
        analyzer.update_fingerprints(paper_dir)
        
        # Second run - no changes
        changes2 = analyzer.detect_changes(paper_dir)
        assert len(changes2['new']) == 0
        assert len(changes2['modified']) == 0
        assert len(changes2['unchanged']) == 1
        assert 'paper1.json' in changes2['unchanged']
    
    def test_change_detection_modified(self, analyzer, temp_dir):
        """Test change detection with modified papers."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        paper_file = os.path.join(paper_dir, "paper1.json")
        
        # Create initial version
        with open(paper_file, 'w') as f:
            json.dump({"title": "Original Title"}, f)
        
        # First detection
        analyzer.detect_changes(paper_dir)
        analyzer.update_fingerprints(paper_dir)
        
        # Modify paper
        with open(paper_file, 'w') as f:
            json.dump({"title": "Modified Title"}, f)
        
        # Detect changes
        changes = analyzer.detect_changes(paper_dir)
        assert len(changes['modified']) == 1
        assert 'paper1.json' in changes['modified']
        assert len(changes['unchanged']) == 0
    
    def test_change_detection_removed(self, analyzer, temp_dir):
        """Test change detection with removed papers."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        # Create two papers
        for i in range(2):
            with open(os.path.join(paper_dir, f"paper{i}.json"), 'w') as f:
                json.dump({"title": f"Paper {i}"}, f)
        
        # First detection
        analyzer.detect_changes(paper_dir)
        analyzer.update_fingerprints(paper_dir)
        
        # Remove one paper
        os.remove(os.path.join(paper_dir, "paper1.json"))
        
        # Detect changes
        changes = analyzer.detect_changes(paper_dir)
        assert len(changes['removed']) == 1
        assert 'paper1.json' in changes['removed']
        assert len(changes['unchanged']) == 1
    
    def test_change_detection_force_flag(self, analyzer, temp_dir):
        """Test force flag treats all papers as modified."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        # Create paper
        with open(os.path.join(paper_dir, "paper1.json"), 'w') as f:
            json.dump({"title": "Test"}, f)
        
        # First run
        analyzer.detect_changes(paper_dir)
        analyzer.update_fingerprints(paper_dir)
        
        # Second run with force
        changes = analyzer.detect_changes(paper_dir, force=True)
        assert len(changes['modified']) == 1
        assert len(changes['unchanged']) == 0
    
    def test_change_detection_pillar_change(self, analyzer, temp_dir):
        """Test pillar change invalidates all caches."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        pillar_file = os.path.join(temp_dir, "pillars.json")
        
        # Create initial pillar file
        with open(pillar_file, 'w') as f:
            json.dump({"pillar1": "value1"}, f)
        
        # Create paper
        with open(os.path.join(paper_dir, "paper1.json"), 'w') as f:
            json.dump({"title": "Test"}, f)
        
        # First run
        analyzer.detect_changes(paper_dir, pillar_file=pillar_file)
        analyzer.update_fingerprints(paper_dir, pillar_file=pillar_file)
        
        # Modify pillar file
        with open(pillar_file, 'w') as f:
            json.dump({"pillar1": "value2"}, f)
        
        # Detect changes - should mark all as modified
        changes = analyzer.detect_changes(paper_dir, pillar_file=pillar_file)
        assert len(changes['modified']) == 1
        assert len(changes['unchanged']) == 0
    
    def test_analysis_caching(self, analyzer, temp_dir):
        """Test saving and retrieving cached analysis."""
        paper_name = "paper1.json"
        stage = "journal_review"
        result = {"status": "complete", "score": 0.85}
        
        # Save analysis
        analyzer.save_analysis(paper_name, stage, result)
        
        # Retrieve analysis
        cached = analyzer.get_cached_analysis(paper_name, stage)
        assert cached == result
    
    def test_analysis_caching_missing(self, analyzer):
        """Test retrieving non-existent cached analysis."""
        cached = analyzer.get_cached_analysis("nonexistent.json", "stage")
        assert cached is None
    
    def test_analysis_caching_multiple_stages(self, analyzer, temp_dir):
        """Test caching multiple stages for same paper."""
        paper_name = "paper1.json"
        
        analyzer.save_analysis(paper_name, "stage1", {"result": "A"})
        analyzer.save_analysis(paper_name, "stage2", {"result": "B"})
        
        assert analyzer.get_cached_analysis(paper_name, "stage1") == {"result": "A"}
        assert analyzer.get_cached_analysis(paper_name, "stage2") == {"result": "B"}
    
    def test_clear_cache_all(self, analyzer):
        """Test clearing all cached analysis."""
        analyzer.save_analysis("paper1.json", "stage1", {"data": 1})
        analyzer.save_analysis("paper2.json", "stage1", {"data": 2})
        
        analyzer.clear_cache()
        
        assert analyzer.get_cached_analysis("paper1.json", "stage1") is None
        assert analyzer.get_cached_analysis("paper2.json", "stage1") is None
    
    def test_clear_cache_specific(self, analyzer):
        """Test clearing cache for specific paper."""
        analyzer.save_analysis("paper1.json", "stage1", {"data": 1})
        analyzer.save_analysis("paper2.json", "stage1", {"data": 2})
        
        analyzer.clear_cache("paper1.json")
        
        assert analyzer.get_cached_analysis("paper1.json", "stage1") is None
        assert analyzer.get_cached_analysis("paper2.json", "stage1") == {"data": 2}
    
    def test_state_persistence(self, temp_dir):
        """Test that state persists across instances."""
        state_file = os.path.join(temp_dir, 'state.json')
        
        # Create first instance and save data
        analyzer1 = IncrementalAnalyzer(state_file=state_file)
        analyzer1.save_analysis("paper1.json", "stage1", {"data": "test"})
        
        # Create second instance and verify data
        analyzer2 = IncrementalAnalyzer(state_file=state_file)
        cached = analyzer2.get_cached_analysis("paper1.json", "stage1")
        
        assert cached == {"data": "test"}
    
    def test_update_fingerprints(self, analyzer, temp_dir):
        """Test fingerprint update functionality."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        # Create papers
        for i in range(2):
            with open(os.path.join(paper_dir, f"paper{i}.json"), 'w') as f:
                json.dump({"title": f"Paper {i}"}, f)
        
        # Update fingerprints
        analyzer.update_fingerprints(paper_dir)
        
        assert len(analyzer.state['paper_fingerprints']) == 2
        assert 'paper0.json' in analyzer.state['paper_fingerprints']
        assert 'paper1.json' in analyzer.state['paper_fingerprints']
        assert analyzer.state['last_run'] is not None
    
    def test_update_fingerprints_removes_deleted(self, analyzer, temp_dir):
        """Test that update_fingerprints removes deleted papers from cache."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        # Create and cache paper
        with open(os.path.join(paper_dir, "paper1.json"), 'w') as f:
            json.dump({"title": "Test"}, f)
        
        analyzer.save_analysis("paper1.json", "stage1", {"data": "test"})
        analyzer.update_fingerprints(paper_dir)
        
        # Remove paper and update again
        os.remove(os.path.join(paper_dir, "paper1.json"))
        analyzer.update_fingerprints(paper_dir)
        
        # Cache should be cleared
        assert analyzer.get_cached_analysis("paper1.json", "stage1") is None
        assert 'paper1.json' not in analyzer.state['paper_fingerprints']
    
    def test_get_stats(self, analyzer, temp_dir):
        """Test statistics retrieval."""
        paper_dir = os.path.join(temp_dir, "papers")
        os.makedirs(paper_dir)
        
        # Create paper
        with open(os.path.join(paper_dir, "paper1.json"), 'w') as f:
            json.dump({"title": "Test"}, f)
        
        analyzer.update_fingerprints(paper_dir)
        analyzer.save_analysis("paper1.json", "stage1", {"data": "test"})
        
        stats = analyzer.get_stats()
        
        assert stats['total_papers_cached'] == 1
        assert stats['papers_with_analysis'] == 1
        assert stats['last_run'] is not None
        assert stats['cache_file'] == analyzer.state_file
    
    def test_initial_state_structure(self, temp_dir):
        """Test initial state has correct structure."""
        state_file = os.path.join(temp_dir, 'state.json')
        analyzer = IncrementalAnalyzer(state_file=state_file)
        
        assert analyzer.state['version'] == '1.0'
        assert analyzer.state['last_run'] is None
        assert analyzer.state['pillar_hash'] is None
        assert analyzer.state['paper_fingerprints'] == {}
        assert analyzer.state['analysis_results'] == {}
    
    def test_large_file_hashing(self, analyzer, temp_dir):
        """Test hashing of larger files (chunked reading)."""
        large_file = os.path.join(temp_dir, "large.json")
        
        # Create a larger file
        large_data = {"data": "x" * 10000}
        with open(large_file, 'w') as f:
            json.dump(large_data, f)
        
        # Hash should work
        hash_val = analyzer._calculate_file_hash(large_file)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 32


class TestIncrementalAnalyzerSingleton:
    """Test singleton instance functionality."""
    
    def test_singleton_returns_same_instance(self):
        """Test that get_incremental_analyzer returns same instance."""
        from literature_review.utils.incremental_analyzer import get_incremental_analyzer
        
        instance1 = get_incremental_analyzer()
        instance2 = get_incremental_analyzer()
        
        assert instance1 is instance2
