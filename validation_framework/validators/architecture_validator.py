"""
Architecture Validator
Validates MASTER_ARCHITECTURE_BLUEPRINT.md against repository structure.
"""

from pathlib import Path
from typing import Set
from ..core.validator import BaseValidator, ValidationReport
from ..core.document_parser import MarkdownParser


class ArchitectureValidator(BaseValidator):
    """Validates architecture documentation against actual codebase"""
    
    tier = 4
    name = "ArchitectureValidator"
    
    def __init__(self, repo_path: Path, gold_standard_path: Path = None):
        super().__init__(repo_path, gold_standard_path)
        self.blueprint_path = repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
    
    def validate(self) -> ValidationReport:
        """Run all architecture validation checks"""
        self.load_gold_standard()
        
        self._check_module_coverage()
        self._check_directory_structure()
        self._check_operationalization_modules()
        self._check_output_files()
        self._check_freshness()
        
        return self.report
    
    def _check_module_coverage(self):
        """T4-ARCH-01: All Python modules documented"""
        test_id = "T4-ARCH-01"
        test_name = "Module Coverage"
        
        try:
            # Get documented modules from blueprint
            documented = self._extract_documented_modules()
            
            # Get actual modules from filesystem
            actual = self._scan_package_modules()
            
            # Compare
            undocumented = actual - documented
            
            if not undocumented:
                self.add_pass(test_id, test_name, "All modules documented", f"{len(actual)} modules")
            else:
                self.add_fail(
                    test_id, test_name,
                    "All modules documented",
                    f"Missing: {len(undocumented)} modules",
                    fix_suggestion=f"Add to docs: {list(undocumented)[:5]}..."
                )
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_directory_structure(self):
        """T4-ARCH-02: Directory structure matches reality"""
        test_id = "T4-ARCH-02"
        test_name = "Directory Structure"
        
        try:
            pkg_path = self.repo_path / "literature_review"
            if not pkg_path.exists():
                self.add_fail(test_id, test_name, "Package exists", "Package not found")
                return
            
            # Count directories
            actual_dirs = set(d.name for d in pkg_path.iterdir() if d.is_dir() and not d.name.startswith('_'))
            expected_dirs = {"analysis", "reviewers", "models", "optimization", "prompts"}
            
            missing = expected_dirs - actual_dirs
            if not missing:
                self.add_pass(test_id, test_name, "Core directories present", f"{len(actual_dirs)} directories")
            else:
                self.add_fail(test_id, test_name, str(expected_dirs), f"Missing: {missing}")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_operationalization_modules(self):
        """T4-ARCH-03: Operationalization modules present"""
        test_id = "T4-ARCH-03"
        test_name = "Operationalization Modules"
        
        required_modules = [
            "literature_review/models/action_vector.py",
            "literature_review/models/validation_strategy.py",
            "literature_review/analysis/validation_tracker.py",
            "literature_review/analysis/action_generator.py",
            "literature_review/analysis/pillar_evolution.py",
            "literature_review/analysis/benchmark_analyzer.py",
        ]
        
        try:
            parser = MarkdownParser(self.blueprint_path)
            content = parser.load()
            
            missing = []
            for mod in required_modules:
                mod_name = Path(mod).name
                if mod_name not in content:
                    missing.append(mod_name)
            
            if not missing:
                self.add_pass(test_id, test_name, f"{len(required_modules)} OP modules", "All present")
            else:
                self.add_fail(test_id, test_name, "All OP modules documented", f"Missing: {missing}")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_output_files(self):
        """T4-ARCH-04: Output files documented"""
        test_id = "T4-ARCH-04"
        test_name = "Output Files Documented"
        
        required_outputs = [
            "action_vectors.json",
            "validation_gap_matrix.json",
            "requirement_benchmark_matrix.json",
            "pillar_research_log.json",
            "pillar_proposals.json",
            "stakeholder_impact_matrix.json",
        ]
        
        try:
            parser = MarkdownParser(self.blueprint_path)
            content = parser.load()
            
            missing = [o for o in required_outputs if o not in content]
            
            if not missing:
                self.add_pass(test_id, test_name, f"{len(required_outputs)} outputs", "All documented")
            else:
                self.add_fail(test_id, test_name, "All outputs documented", f"Missing: {missing}")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _check_freshness(self):
        """T4-ARCH-05: Document freshness"""
        test_id = "T4-ARCH-05"
        test_name = "Document Freshness"
        
        try:
            import os
            from datetime import datetime, timedelta
            
            if not self.blueprint_path.exists():
                self.add_fail(test_id, test_name, "Document exists", "Not found")
                return
            
            mtime = datetime.fromtimestamp(os.path.getmtime(self.blueprint_path))
            age_days = (datetime.now() - mtime).days
            max_age = 7
            
            if age_days <= max_age:
                self.add_pass(test_id, test_name, f"≤{max_age} days", f"{age_days} days old")
            else:
                self.add_fail(test_id, test_name, f"≤{max_age} days", f"{age_days} days old",
                             fix_suggestion="Update MASTER_ARCHITECTURE_BLUEPRINT.md")
        except Exception as e:
            self.add_error(test_id, test_name, e)
    
    def _extract_documented_modules(self) -> Set[str]:
        """Extract module names from blueprint code blocks"""
        parser = MarkdownParser(self.blueprint_path)
        code_blocks = parser.extract_code_blocks()
        
        modules = set()
        for lang, content in code_blocks:
            for line in content.splitlines():
                if '.py' in line:
                    # Extract filename
                    parts = line.split()
                    for part in parts:
                        if '.py' in part:
                            name = part.replace('├──', '').replace('└──', '').replace('│', '').strip()
                            if name.endswith('.py'):
                                modules.add(name)
        return modules
    
    def _scan_package_modules(self) -> Set[str]:
        """Scan actual Python modules in literature_review/"""
        modules = set()
        pkg_path = self.repo_path / "literature_review"
        
        if pkg_path.exists():
            for py_file in pkg_path.rglob("*.py"):
                if not py_file.name.startswith('test_'):
                    modules.add(py_file.name)
        
        return modules
