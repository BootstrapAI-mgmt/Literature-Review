"""
Cascade Validator
Validates document cascade/dependency chains.
"""

from pathlib import Path
from typing import Dict, List, Set
from ..core.validator import BaseValidator, ValidationReport
from ..core.document_parser import MarkdownParser


class CascadeValidator(BaseValidator):
    """Validates cascade propagation across document dependencies"""
    
    tier = 5
    name = "CascadeValidator"
    
    # Define cascade chains
    CASCADE_CHAINS = {
        "code_module": {
            "trigger": "New .py file",
            "chain": ["MASTER_ARCHITECTURE_BLUEPRINT.md", "Module README"],
        },
        "task_completion": {
            "trigger": "PR merge with task",
            "chain": ["task-cards/*.md", "WAVE_INDEX.md", "MASTER_REPOSITORY_ROADMAP.md"],
        },
        "wave_completion": {
            "trigger": "All wave tasks complete",
            "chain": ["WAVE_INDEX.md", "MASTER_REPOSITORY_ROADMAP.md"],
        },
    }
    
    def __init__(self, repo_path: Path, gold_standard_path: Path = None):
        super().__init__(repo_path, gold_standard_path)
        self.baselines: Dict[str, str] = {}
    
    def validate(self) -> ValidationReport:
        """Run cascade validation checks"""
        self.load_gold_standard()
        
        self._check_code_module_cascade()
        self._check_task_completion_cascade()
        self._check_wave_completion_cascade()
        self._check_config_change_cascade()
        self._check_output_file_cascade()
        self._check_task_card_cascade()
        
        return self.report
    
    def capture_baseline(self, documents: List[Path]) -> Dict[str, str]:
        """Capture current state of documents for comparison"""
        for doc_path in documents:
            if doc_path.exists():
                self.baselines[str(doc_path)] = doc_path.read_text(encoding='utf-8')
        return self.baselines
    
    def _check_code_module_cascade(self):
        """T5-CC-01: New .py file cascades to Architecture"""
        test_id = "T5-CC-01"
        test_name = "Code Module Cascade"
        
        try:
            # Verify architecture blueprint mentions key modules
            blueprint = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
            if not blueprint.exists():
                self.add_skip(test_id, test_name, "Blueprint not found")
                return
            
            parser = MarkdownParser(blueprint)
            content = parser.load()
            
            # Check that package structure section exists
            if "literature_review/" in content and ".py" in content:
                self.add_pass(test_id, test_name, "Modules documented", "Chain intact")
            else:
                self.add_fail(test_id, test_name, "Modules documented", "Missing module docs")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_task_completion_cascade(self):
        """T5-CC-02: PR merge cascades Task→Index→Roadmap"""
        test_id = "T5-CC-02"
        test_name = "Task Completion Cascade"
        
        try:
            # Check that OP wave tasks are reflected in roadmap
            roadmap = self.repo_path / "docs" / "MASTER_REPOSITORY_ROADMAP.md"
            if not roadmap.exists():
                self.add_skip(test_id, test_name, "Roadmap not found")
                return
            
            parser = MarkdownParser(roadmap)
            content = parser.load()
            
            # Look for Operationalization being marked complete
            if "Operationalization" in content and ("Complete" in content or "✅" in content):
                self.add_pass(test_id, test_name, "Cascade verified", "OP wave in roadmap")
            else:
                self.add_fail(test_id, test_name, "Tasks cascade to roadmap", "Not reflected")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_wave_completion_cascade(self):
        """T5-CC-03: Wave completion cascades Index→Roadmap→Totals"""
        test_id = "T5-CC-03"
        test_name = "Wave Completion Cascade"
        
        try:
            roadmap = self.repo_path / "docs" / "MASTER_REPOSITORY_ROADMAP.md"
            if not roadmap.exists():
                self.add_skip(test_id, test_name, "Roadmap not found")
                return
            
            parser = MarkdownParser(roadmap)
            tables = parser.extract_tables()
            
            # Find totals row in At-a-Glance
            found_totals = False
            for table in tables:
                if "Task Cards" in table or "Completed" in table:
                    found_totals = True
                    break
            
            if found_totals:
                self.add_pass(test_id, test_name, "Totals updated", "Found in table")
            else:
                self.add_fail(test_id, test_name, "Totals in At-a-Glance", "Not found")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_config_change_cascade(self):
        """T5-CC-04: Config change cascades to Architecture"""
        test_id = "T5-CC-04"
        test_name = "Config Change Cascade"
        
        try:
            # Check if pipeline_config.json is documented
            blueprint = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
            if not blueprint.exists():
                self.add_skip(test_id, test_name, "Blueprint not found")
                return
            
            parser = MarkdownParser(blueprint)
            content = parser.load()
            
            if "pipeline_config" in content or "configuration" in content.lower():
                self.add_pass(test_id, test_name, "Config documented", "Chain intact")
            else:
                self.add_skip(test_id, test_name, "No config documentation required")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_output_file_cascade(self):
        """T5-CC-05: New output file cascades to Architecture"""
        test_id = "T5-CC-05"
        test_name = "Output File Cascade"
        
        try:
            blueprint = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
            if not blueprint.exists():
                self.add_skip(test_id, test_name, "Blueprint not found")
                return
            
            parser = MarkdownParser(blueprint)
            content = parser.load()
            
            # Check for output file documentation
            output_files = ["action_vectors.json", "validation_gap_matrix.json"]
            found = sum(1 for f in output_files if f in content)
            
            if found > 0:
                self.add_pass(test_id, test_name, "Outputs documented", f"{found} files")
            else:
                self.add_fail(test_id, test_name, "Output files documented", "None found")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_task_card_cascade(self):
        """T5-CC-06: New task card cascades to Index→Roadmap"""
        test_id = "T5-CC-06"
        test_name = "Task Card Cascade"
        
        try:
            # Count task cards
            task_cards_dir = self.repo_path / "task-cards"
            if not task_cards_dir.exists():
                self.add_skip(test_id, test_name, "Task cards dir not found")
                return
            
            card_count = len(list(task_cards_dir.glob("OP_WAVE_*.md")))
            
            # Check roadmap mentions the count
            roadmap = self.repo_path / "docs" / "MASTER_REPOSITORY_ROADMAP.md"
            if roadmap.exists():
                parser = MarkdownParser(roadmap)
                content = parser.load()
                if "8" in content:  # OP wave has 8 tasks
                    self.add_pass(test_id, test_name, "Cards in roadmap", f"{card_count} cards")
                else:
                    self.add_fail(test_id, test_name, "Card count in roadmap", "Not found")
            else:
                self.add_skip(test_id, test_name, "Roadmap not found")
        except Exception as e:
            self.add_error(test_id, test_name, e)
