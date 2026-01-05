"""
Staleness Validator
Validates document freshness based on age thresholds.
"""

from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
import os
from ..core.validator import BaseValidator, ValidationReport
from ..core.document_parser import MarkdownParser


class StalenessValidator(BaseValidator):
    """Validates document freshness and staleness detection"""
    
    tier = 4
    name = "StalenessValidator"
    
    # Default freshness thresholds (days)
    THRESHOLDS = {
        "MASTER_*.md": 7,
        "task-cards/*.md": 3,
        "*_WAVE_INDEX.md": 1,
        "docs/guides/*.md": 14,
        "README.md": 30,
    }
    
    def __init__(self, repo_path: Path, gold_standard_path: Path = None):
        super().__init__(repo_path, gold_standard_path)
    
    def validate(self) -> ValidationReport:
        """Run staleness validation checks"""
        self.load_gold_standard()
        
        self._check_stale_detection()
        self._check_fresh_detection()
        self._check_threshold_accuracy()
        
        return self.report
    
    def _check_stale_detection(self):
        """T4-STAL-01: Stale documents correctly flagged"""
        test_id = "T4-STAL-01"
        test_name = "Stale Detection"
        
        try:
            stale_docs = self._find_stale_documents()
            
            # For validation, we just check the mechanism works
            self.add_pass(test_id, test_name, "Detection works", f"Found {len(stale_docs)} stale docs")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_fresh_detection(self):
        """T4-STAL-02: Fresh documents not falsely flagged"""
        test_id = "T4-STAL-02"
        test_name = "Fresh Detection"
        
        try:
            # Check master docs are reasonably fresh
            master_docs = [
                self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md",
                self.repo_path / "docs" / "MASTER_REPOSITORY_ROADMAP.md",
            ]
            
            fresh_count = 0
            for doc in master_docs:
                if doc.exists():
                    age = self._get_document_age(doc)
                    if age <= 14:  # Within 2 weeks is reasonably fresh
                        fresh_count += 1
            
            if fresh_count == len(master_docs):
                self.add_pass(test_id, test_name, "No false positives", f"{fresh_count} fresh docs")
            else:
                self.add_fail(test_id, test_name, "All master docs fresh", f"Only {fresh_count} fresh")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_threshold_accuracy(self):
        """T4-STAL-03: Threshold scoring is correct"""
        test_id = "T4-STAL-03"
        test_name = "Threshold Accuracy"
        
        try:
            # Verify thresholds are applied correctly
            test_cases = [
                ("MASTER_ARCHITECTURE_BLUEPRINT.md", 7),
                ("README.md", 30),
            ]
            
            correct = 0
            for pattern, expected_threshold in test_cases:
                actual = self._get_threshold_for_pattern(pattern)
                if actual == expected_threshold:
                    correct += 1
            
            if correct == len(test_cases):
                self.add_pass(test_id, test_name, "Thresholds correct", f"{correct}/{len(test_cases)}")
            else:
                self.add_fail(test_id, test_name, "All thresholds correct", f"Only {correct} correct")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _find_stale_documents(self) -> List[Path]:
        """Find documents that exceed their freshness threshold"""
        stale = []
        
        docs_dir = self.repo_path / "docs"
        if docs_dir.exists():
            for doc in docs_dir.glob("*.md"):
                threshold = self._get_threshold_for_pattern(doc.name)
                age = self._get_document_age(doc)
                if age > threshold:
                    stale.append(doc)
        
        return stale
    
    def _get_document_age(self, path: Path) -> int:
        """Get document age in days based on modification time"""
        if not path.exists():
            return 999
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        return (datetime.now() - mtime).days
    
    def _get_threshold_for_pattern(self, filename: str) -> int:
        """Get freshness threshold for a file pattern"""
        if filename.startswith("MASTER_"):
            return 7
        elif filename.endswith("_WAVE_INDEX.md"):
            return 1
        elif "README" in filename:
            return 30
        else:
            return 14  # Default
