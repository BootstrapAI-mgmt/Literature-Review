# tests/e2e/test_documentation_sync.py
"""
Gold Standard Validation Suite for n8n-GitHub Documentation Automation

Run after each n8n workflow execution to verify documentation accuracy. 
"""

import os
import re
import json
from pathlib import Path
# from github import Github # Commenting out for now to focus on local file validation first and avoid dependency issues immediately
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple

@dataclass
class ValidationResult:
    test_name: str
    passed: bool
    expected: str
    actual: str
    gap_description: str = ""

class GoldStandardValidator:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.results: List[ValidationResult] = []
        
    def validate_architecture_blueprint(self) -> List[ValidationResult]: 
        """Validate MASTER_ARCHITECTURE_BLUEPRINT.md reflects actual structure"""
        results = []
        
        # 1. Parse documented structure
        blueprint_path = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
        if not blueprint_path.exists():
             return [ValidationResult("Architecture Blueprint Existence", False, "File exists", "File missing", "Create file")]

        documented_modules = self._extract_documented_modules(blueprint_path)
        
        # 2. Scan actual structure (entire repo related to python)
        actual_modules = self._scan_package_structure("")
        
        # Filter out test files and transient scripts for high-level architecture validation
        actual_modules = {
            m for m in actual_modules 
            if not m.startswith("test_") 
            and not m.endswith("_test.py") 
            and m not in ["flaky_script.py", "success_script.py", "permanent_error_script.py"]
        }
        
        # 3. Compare
        missing_from_docs = actual_modules - documented_modules
        stale_in_docs = {
            m for m in (documented_modules - actual_modules)
            if not m.startswith("test_") 
            and not m.endswith("_test.py")
        }
        
        results.append(ValidationResult(
            test_name="Architecture: No undocumented modules",
            passed=len(missing_from_docs) == 0,
            expected="All modules documented",
            actual=f"Missing: {missing_from_docs}" if missing_from_docs else "All documented",
            gap_description=f"Add these to docs: {missing_from_docs}"
        ))
        
        results.append(ValidationResult(
            test_name="Architecture: No stale module references",
            passed=len(stale_in_docs) == 0,
            expected="All documented modules exist",
            actual=f"Stale: {stale_in_docs}" if stale_in_docs else "All exist",
            gap_description=f"Remove these from docs: {stale_in_docs}"
        ))
        
        return results
    
    def validate_roadmap_task_status(self) -> List[ValidationResult]: 
        """Validate MASTER_REPOSITORY_ROADMAP.md task statuses match reality"""
        results = []
        
        # Check Operationalization Wave specifically
        roadmap_path = self.repo_path / "docs" / "MASTER_REPOSITORY_ROADMAP.md"
        if not roadmap_path.exists():
            return [ValidationResult("Roadmap Existence", False, "File exists", "File missing", "Create file")]

        roadmap = self._parse_roadmap(roadmap_path)
        op_wave_status = roadmap.get("operationalization_wave", {})
        
        # Based on merged PRs #97-105, this should be COMPLETE
        results.append(ValidationResult(
            test_name="Roadmap: Operationalization Wave Status",
            passed=op_wave_status.get("completion") == "100%",
            expected="100% Complete (PRs #97-105 merged)",
            actual=f"{op_wave_status.get('completion', 'Unknown')}",
            gap_description="Update wave status to [PASS] Complete based on merged PRs"
        ))
        
        return results
    
    # Placeholder for PR sync validation to avoid PyGithub dependency for now
    def validate_task_card_pr_sync(self) -> List[ValidationResult]:
        """Validate task cards reflect merged PR status (Local check only for now)"""
        results = []
        
        # Map of PRs to task cards that should be complete
        # Hardcoded for simulation of local state check
        task_ids = [
            "OP_WAVE_1_1_SCHEMA_FOUNDATION",
            "OP_WAVE_2_1_ACTION_EXTRACTION", 
            "OP_WAVE_2_2_BENCHMARK_EXTRACTION",
            "OP_WAVE_3_1_VALIDATION_TRACKER",
            "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR",
            "OP_WAVE_4_1_PILLAR_RESEARCH_LOG",
            "OP_WAVE_4_2_MODIFICATION_PROPOSALS",
            "OP_WAVE_4_3_STAKEHOLDER_MATRIX",
        ]
        
        for task_id in task_ids:
            task_path = self.repo_path / "task-cards" / f"{task_id}.md"
            if task_path.exists():
                content = task_path.read_text(encoding='utf-8')
                is_complete = "Status: [PASS] Complete" in content or "Status:** Complete" in content or "Status: Complete" in content or "✅ Complete" in content
                
                results.append(ValidationResult(
                    test_name=f"Task Card Sync: {task_id}",
                    passed=is_complete,
                    expected=f"Status: Complete",
                    actual="Complete" if is_complete else "Not marked complete",
                    gap_description=f"Update {task_id} status to Complete"
                ))
            else:
                 results.append(ValidationResult(
                    test_name=f"Task Card Existence: {task_id}",
                    passed=False,
                    expected=f"File exists",
                    actual="File missing",
                    gap_description=f"Create task card {task_id}"
                ))
        
        return results
    
    def run_full_validation(self) -> Dict[str, any]:
        """Run all validations and return comprehensive report"""
        all_results = []
        all_results.extend(self.validate_architecture_blueprint())
        all_results.extend(self.validate_roadmap_task_status())
        all_results.extend(self.validate_task_card_pr_sync())
        
        passed = sum(1 for r in all_results if r.passed)
        total = len(all_results)
        
        return {
            "summary": {
                "passed": passed,
                "failed": total - passed,
                "total": total,
                "pass_rate": f"{(passed/total)*100:.1f}%"
            },
            "results": [
                {
                    "test": r.test_name,
                    "passed": r.passed,
                    "expected": r.expected,
                    "actual": r.actual,
                    "remediation": r.gap_description
                }
                for r in all_results
            ],
            "critical_gaps": [
                r for r in all_results 
                if not r.passed and ("Operationalization" in r.test_name or "Architecture" in r.test_name)
            ]
        }
    
    # Helper methods
    def _extract_documented_modules(self, path: Path) -> Set[str]:
        """Extract module paths from architecture blueprint markdown"""
        if not path.exists(): return set()
        content = path.read_text(encoding='utf-8')
        # Parse all code blocks
        modules = set()
        code_block_pattern = r'```[\s\S]*?```'
        code_blocks = re.findall(code_block_pattern, content)
        
        for block in code_blocks:
            for line in block.split('\n'):
                if '.py' in line: 
                    # Extract filename
                    match = re.search(r'(\w+\.py)', line)
                    if match:
                        modules.add(match.group(1))
        return modules
    
    def _scan_package_structure(self, package: str) -> Set[str]:
        """Scan actual Python package (or ALL packages) for module files"""
        modules = set()
        
        # Scan literature_review
        pkg_path = self.repo_path / "literature_review"
        if pkg_path.exists():
            for py_file in pkg_path.rglob("*.py"):
                modules.add(py_file.name)
                
        # Scan webdashboard
        dash_path = self.repo_path / "webdashboard"
        if dash_path.exists():
            for py_file in dash_path.rglob("*.py"):
                modules.add(py_file.name)
                
        # Scan scripts
        scripts_path = self.repo_path / "scripts"
        if scripts_path.exists():
            for py_file in scripts_path.rglob("*.py"):
                modules.add(py_file.name)
                
        # Scan root files (explicit list or glob)
        for py_file in self.repo_path.glob("*.py"):
            modules.add(py_file.name)
            
        # Scan tests too since they are documented
        tests_path = self.repo_path / "tests"
        if tests_path.exists():
            for py_file in tests_path.rglob("*.py"):
                modules.add(py_file.name)

        return modules
    
    def _parse_roadmap(self, path: Path) -> Dict: 
        """Parse roadmap for wave status information"""
        if not path.exists(): return {}
        content = path.read_text(encoding='utf-8')
        
        # Simple extraction of Operationalization Wave status
        result = {}
        if "Operationalization Wave" in content: 
            # Look for status indicator
            if "📋 Planned" in content: 
                result["operationalization_wave"] = {"completion": "0%"}
            elif "[PASS] Complete" in content or "✅ Complete" in content:
                result["operationalization_wave"] = {"completion": "100%"}
            else:
                 result["operationalization_wave"] = {"completion": "Unknown"}
        
        return result


if __name__ == "__main__":
    try:
        validator = GoldStandardValidator(".")
        report = validator.run_full_validation()
        
        print("\n" + "="*60)
        print("GOLD STANDARD VALIDATION REPORT (V2.0.0)")
        print("="*60)
        print(f"\nSummary: {report['summary']['passed']}/{report['summary']['total']} passed ({report['summary']['pass_rate']})")
        
        if report['summary']['failed'] > 0:
            print("\n[FAIL] FAILURES:")
            for r in report['results']:
                if not r['passed']:
                    print(f"\n  Test: {r['test']}")
                    print(f"  Expected: {r['expected']}")
                    print(f"  Actual: {r['actual']}")
                    print(f"  Fix: {r['remediation']}")
        else:
            print("\n[PASS] ALL TESTS PASSED")
        
        print("\n" + "="*60)
    except Exception as e:
        print(f"Validation Error: {e}")
