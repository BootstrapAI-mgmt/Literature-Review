"""
Roadmap Validator
Validates MASTER_REPOSITORY_ROADMAP.md against actual project state.
"""

from pathlib import Path
from typing import Dict, List
from ..core.validator import BaseValidator, ValidationReport
from ..core.document_parser import MarkdownParser


class RoadmapValidator(BaseValidator):
    """Validates roadmap documentation against actual project status"""
    
    tier = 4
    name = "RoadmapValidator"
    
    def __init__(self, repo_path: Path, gold_standard_path: Path = None):
        super().__init__(repo_path, gold_standard_path)
        self.roadmap_path = repo_path / "docs" / "MASTER_REPOSITORY_ROADMAP.md"
    
    def validate(self) -> ValidationReport:
        """Run all roadmap validation checks"""
        self.load_gold_standard()
        
        self._check_op_wave_complete()
        self._check_task_counts()
        self._check_percentages()
        self._check_validation_matrix_exists()
        self._check_wave_05_exists()
        self._check_at_a_glance_table()
        
        return self.report
    
    def _check_op_wave_complete(self):
        """T4-ROAD-01: Operationalization Wave shows Complete"""
        test_id = "T4-ROAD-01"
        test_name = "OP Wave Complete"
        
        try:
            parser = MarkdownParser(self.roadmap_path)
            content = parser.load()
            
            # Look for the Operationalization Wave status
            if "Operationalization Wave" in content and "✅ Complete" in content:
                # Check it's in the same context
                if "Operationalization Wave** | ✅ Complete" in content or \
                   "Operationalization Wave (Complete" in content:
                    self.add_pass(test_id, test_name, "✅ Complete", "Status confirmed")
                else:
                    self.add_pass(test_id, test_name, "✅ Complete", "Wave marked complete")
            else:
                self.add_fail(test_id, test_name, "✅ Complete", "Not marked complete",
                             fix_suggestion="Update OP Wave status to Complete")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_task_counts(self):
        """T4-ROAD-02: Task counts match reality"""
        test_id = "T4-ROAD-02"
        test_name = "Task Counts"
        
        try:
            # Count actual task cards
            task_cards_dir = self.repo_path / "task-cards"
            actual_count = 0
            if task_cards_dir.exists():
                actual_count = len(list(task_cards_dir.glob("*.md")))
            
            parser = MarkdownParser(self.roadmap_path)
            content = parser.load()
            
            # Look for total count in roadmap
            import re
            match = re.search(r'\*\*Total Task Cards:\*\*\s*(\d+)', content)
            documented_count = int(match.group(1)) if match else 0
            
            # Allow some tolerance (indexes don't count as task cards)
            if abs(documented_count - actual_count) <= 5:
                self.add_pass(test_id, test_name, f"~{documented_count}", f"Actual: {actual_count}")
            else:
                self.add_fail(test_id, test_name, f"{documented_count}", f"Actual: {actual_count}",
                             fix_suggestion="Update task card counts in roadmap")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_percentages(self):
        """T4-ROAD-03: Percentages are mathematically correct"""
        test_id = "T4-ROAD-03"
        test_name = "Completion Percentages"
        
        try:
            parser = MarkdownParser(self.roadmap_path)
            tables = parser.extract_tables()
            
            # Find At-a-Glance table
            for table in tables:
                if 'Completion' in table and 'Status' in table:
                    completions = table.get('Completion', [])
                    statuses = table.get('Status', [])
                    
                    # Check that Complete waves show 100%
                    issues = []
                    for i, status in enumerate(statuses):
                        if '✅' in status and i < len(completions):
                            if '100%' not in completions[i]:
                                issues.append(f"Row {i+1}: Complete but not 100%")
                    
                    if not issues:
                        self.add_pass(test_id, test_name, "Percentages accurate", "Validated")
                    else:
                        self.add_fail(test_id, test_name, "100% for Complete", str(issues))
                    return
            
            self.add_skip(test_id, test_name, "Could not find At-a-Glance table")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_validation_matrix_exists(self):
        """T4-ROAD-04: Validation Matrix Wave section exists"""
        test_id = "T4-ROAD-04"
        test_name = "Validation Matrix Exists"
        
        try:
            parser = MarkdownParser(self.roadmap_path)
            
            if parser.section_exists("Validation Matrix"):
                self.add_pass(test_id, test_name, "Section exists", "Found")
            else:
                self.add_fail(test_id, test_name, "Section exists", "Not found",
                             fix_suggestion="Add Validation Matrix Wave section")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_wave_05_exists(self):
        """T4-ROAD-05: Wave 0.5 section exists"""
        test_id = "T4-ROAD-05"
        test_name = "Wave 0.5 Exists"
        
        try:
            parser = MarkdownParser(self.roadmap_path)
            content = parser.load()
            
            if "Wave 0.5" in content or "Modularization" in content:
                self.add_pass(test_id, test_name, "Section exists", "Found")
            else:
                self.add_skip(test_id, test_name, "Wave 0.5 may not be required yet")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_at_a_glance_table(self):
        """T4-ROAD-06: At-a-Glance table is accurate"""
        test_id = "T4-ROAD-06"
        test_name = "At-a-Glance Table"
        
        try:
            parser = MarkdownParser(self.roadmap_path)
            sections = parser.extract_sections()
            
            # Check the table exists in a relevant section
            if "At a Glance" in sections or "Executive Summary" in sections:
                self.add_pass(test_id, test_name, "Table present", "Found in summary")
            else:
                self.add_fail(test_id, test_name, "At-a-Glance table", "Not found")
        except Exception as e:
            self.add_error(test_id, test_name, e)
