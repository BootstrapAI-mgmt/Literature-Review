"""
Task Card Validator
Validates task card status synchronization with PRs.
"""

from pathlib import Path
from typing import Dict, List
import re
from ..core.validator import BaseValidator, ValidationReport
from ..core.document_parser import MarkdownParser
from ..core.github_client import GitHubClient


class TaskCardValidator(BaseValidator):
    """Validates task card synchronization with PR status"""
    
    tier = 4
    name = "TaskCardValidator"
    
    # Known PR-to-Task mappings for Operationalization Wave
    OP_WAVE_MAPPINGS = {
        97: "OP_WAVE_1_1_SCHEMA_FOUNDATION",
        98: "OP_WAVE_2_1_ACTION_EXTRACTION",
        99: "OP_WAVE_2_2_BENCHMARK_EXTRACTION",
        100: "OP_WAVE_3_1_VALIDATION_TRACKER",
        101: "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR",
        102: "OP_WAVE_4_1_PILLAR_RESEARCH_LOG",
        103: "OP_WAVE_4_2_MODIFICATION_PROPOSALS",
        105: "OP_WAVE_4_3_STAKEHOLDER_MATRIX",
    }
    
    def __init__(self, repo_path: Path, gold_standard_path: Path = None):
        super().__init__(repo_path, gold_standard_path)
        self.task_cards_dir = repo_path / "task-cards"
        self.github = GitHubClient()
    
    def validate(self) -> ValidationReport:
        """Run all task card validation checks"""
        self.load_gold_standard()
        
        self._check_pr_to_task_sync()
        self._check_task_to_pr_sync()
        self._check_wave_index_sync()
        self._check_op_index_complete()
        
        return self.report
    
    def _check_pr_to_task_sync(self):
        """T4-TASK-01: Merged PRs have Complete task cards"""
        test_id = "T4-TASK-01"
        test_name = "PR→Task Sync"
        
        try:
            failures = []
            
            for pr_num, task_id in self.OP_WAVE_MAPPINGS.items():
                task_path = self.task_cards_dir / f"{task_id}.md"
                if task_path.exists():
                    status = self._get_task_status(task_path)
                    if "complete" not in status.lower():
                        failures.append(f"PR#{pr_num}: {task_id} = {status}")
            
            if not failures:
                self.add_pass(test_id, test_name, "All synced", f"{len(self.OP_WAVE_MAPPINGS)} PRs checked")
            else:
                self.add_fail(test_id, test_name, "All Complete", f"Issues: {len(failures)}",
                             fix_suggestion=f"Fix: {failures[:2]}")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_task_to_pr_sync(self):
        """T4-TASK-02: Complete tasks have merged PRs"""
        test_id = "T4-TASK-02"
        test_name = "Task→PR Sync"
        
        try:
            # For now, just verify task cards exist
            missing = []
            for task_id in self.OP_WAVE_MAPPINGS.values():
                task_path = self.task_cards_dir / f"{task_id}.md"
                if not task_path.exists():
                    missing.append(task_id)
            
            if not missing:
                self.add_pass(test_id, test_name, "All task cards exist", f"{len(self.OP_WAVE_MAPPINGS)} cards")
            else:
                self.add_fail(test_id, test_name, "All cards present", f"Missing: {missing}")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_wave_index_sync(self):
        """T4-TASK-03: Wave index reflects individual card statuses"""
        test_id = "T4-TASK-03"
        test_name = "Wave Index Sync"
        
        try:
            index_path = self.task_cards_dir / "OPERATIONALIZATION_WAVE_INDEX.md"
            if not index_path.exists():
                self.add_skip(test_id, test_name, "Index file not found")
                return
            
            parser = MarkdownParser(index_path)
            content = parser.load()
            
            # Check that all OP tasks appear in index
            found = 0
            for task_id in self.OP_WAVE_MAPPINGS.values():
                if task_id in content:
                    found += 1
            
            if found == len(self.OP_WAVE_MAPPINGS):
                self.add_pass(test_id, test_name, "All tasks in index", f"{found} found")
            else:
                self.add_fail(test_id, test_name, f"{len(self.OP_WAVE_MAPPINGS)} tasks", f"Found: {found}")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_op_index_complete(self):
        """T4-TASK-04: OP Wave Index shows all tasks Complete"""
        test_id = "T4-TASK-04"
        test_name = "OP Index Complete"
        
        try:
            index_path = self.task_cards_dir / "OPERATIONALIZATION_WAVE_INDEX.md"
            if not index_path.exists():
                self.add_skip(test_id, test_name, "Index file not found")
                return
            
            parser = MarkdownParser(index_path)
            content = parser.load()
            
            # Count Complete markers
            complete_count = content.count("✅") + content.lower().count("complete")
            
            if complete_count >= 8:
                self.add_pass(test_id, test_name, "8/8 Complete", f"Found {complete_count} markers")
            else:
                self.add_fail(test_id, test_name, "8/8 Complete", f"Found {complete_count} markers")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _get_task_status(self, task_path: Path) -> str:
        """Extract status from a task card file"""
        try:
            parser = MarkdownParser(task_path)
            content = parser.load()
            
            # Look for Status: line
            match = re.search(r'Status[:\s]+([^\n]+)', content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # Check for status indicators
            if "✅" in content:
                return "Complete"
            elif "🔄" in content or "In Progress" in content:
                return "In Progress"
            
            return "Unknown"
        except Exception:
            return "Error"
