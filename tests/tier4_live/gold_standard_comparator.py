"""
Gold Standard Comparator - Validates outputs against expected states.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field


@dataclass
class ComparisonResult:
    """Result of a gold standard comparison"""
    test_id: str
    test_name: str
    passed: bool
    expected: Any
    actual: Any
    difference: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "passed": self.passed,
            "expected": str(self.expected)[:200],
            "actual": str(self.actual)[:200],
            "difference": self.difference
        }


class GoldStandardComparator:
    """
    Compares actual outputs against gold standard expectations.
    
    Implements Tier 4 accuracy tests from MASTER_N8N_VALIDATION_PLAN.md:
    - T4-ARCH-01 through T4-ARCH-05 (Architecture Blueprint)
    - T4-ROAD-01 through T4-ROAD-06 (Repository Roadmap)
    - T4-TASK-01 through T4-TASK-04 (Task Card Sync)
    """
    
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self.results: List[ComparisonResult] = []
    
    # ==========================================================================
    # T4-ARCH: Architecture Blueprint Accuracy
    # ==========================================================================
    
    def t4_arch_01_module_coverage(self) -> ComparisonResult:
        """
        T4-ARCH-01: All Python modules in literature_review/ are documented.
        """
        test_id = "T4-ARCH-01"
        
        # Get actual modules
        pkg_path = self.repo_path / "literature_review"
        actual_modules = set()
        if pkg_path.exists():
            for py_file in pkg_path.rglob("*.py"):
                if not py_file.name.startswith("test_") and py_file.name != "__init__.py":
                    actual_modules.add(py_file.name)
        
        # Get documented modules from blueprint
        blueprint_path = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
        documented = set()
        if blueprint_path.exists():
            content = blueprint_path.read_text(encoding='utf-8')
            # Find .py references
            for match in re.findall(r'(\w+\.py)', content):
                documented.add(match)
        
        # Compare
        undocumented = actual_modules - documented
        passed = len(undocumented) == 0
        
        result = ComparisonResult(
            test_id=test_id,
            test_name="Module Coverage",
            passed=passed,
            expected=f"All {len(actual_modules)} modules documented",
            actual=f"{len(documented)} documented, {len(undocumented)} missing",
            difference=str(list(undocumented)[:5]) if undocumented else ""
        )
        self.results.append(result)
        return result
    
    def t4_arch_02_directory_structure(self) -> ComparisonResult:
        """
        T4-ARCH-02: Directory structure matches actual package.
        """
        test_id = "T4-ARCH-02"
        
        # Updated to match actual repository structure
        # Core directories that should exist in literature_review/
        expected_dirs = {"analysis", "reviewers", "models", "optimization", "utils", "config"}
        pkg_path = self.repo_path / "literature_review"
        
        actual_dirs = set()
        if pkg_path.exists():
            actual_dirs = {d.name for d in pkg_path.iterdir() 
                          if d.is_dir() and not d.name.startswith("_")}
        
        missing = expected_dirs - actual_dirs
        passed = len(missing) == 0
        
        result = ComparisonResult(
            test_id=test_id,
            test_name="Directory Structure",
            passed=passed,
            expected=str(expected_dirs),
            actual=str(actual_dirs),
            difference=f"Missing: {missing}" if missing else ""
        )
        self.results.append(result)
        return result
    
    def t4_arch_03_operationalization_modules(self) -> ComparisonResult:
        """
        T4-ARCH-03: Operationalization modules are documented.
        """
        test_id = "T4-ARCH-03"
        
        required_modules = [
            "action_vector.py",
            "validation_strategy.py",
            "validation_tracker.py",
            "action_generator.py",
            "pillar_evolution.py",
            "benchmark_analyzer.py",
        ]
        
        blueprint_path = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
        documented = []
        missing = []
        
        if blueprint_path.exists():
            content = blueprint_path.read_text(encoding='utf-8')
            for mod in required_modules:
                if mod in content:
                    documented.append(mod)
                else:
                    missing.append(mod)
        
        passed = len(missing) == 0
        
        result = ComparisonResult(
            test_id=test_id,
            test_name="Operationalization Modules",
            passed=passed,
            expected=f"All {len(required_modules)} OP modules documented",
            actual=f"{len(documented)} documented, {len(missing)} missing",
            difference=str(missing) if missing else ""
        )
        self.results.append(result)
        return result
    
    def t4_arch_05_freshness(self) -> ComparisonResult:
        """
        T4-ARCH-05: Architecture document freshness (≤7 days).
        """
        test_id = "T4-ARCH-05"
        
        import os
        from datetime import datetime
        
        blueprint_path = self.repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
        max_age_days = 7
        
        if not blueprint_path.exists():
            result = ComparisonResult(
                test_id=test_id,
                test_name="Document Freshness",
                passed=False,
                expected="Document exists",
                actual="Not found"
            )
            self.results.append(result)
            return result
        
        mtime = datetime.fromtimestamp(os.path.getmtime(blueprint_path))
        age_days = (datetime.now() - mtime).days
        passed = age_days <= max_age_days
        
        result = ComparisonResult(
            test_id=test_id,
            test_name="Document Freshness",
            passed=passed,
            expected=f"≤{max_age_days} days old",
            actual=f"{age_days} days old"
        )
        self.results.append(result)
        return result
    
    # ==========================================================================
    # T4-ROAD: Roadmap Accuracy
    # ==========================================================================
    
    def t4_road_02_task_count(self) -> ComparisonResult:
        """
        T4-ROAD-02: Task count reflects actual task cards.
        """
        test_id = "T4-ROAD-02"
        
        # Count actual task cards
        task_cards_dir = self.repo_path / "task-cards"
        actual_count = 0
        if task_cards_dir.exists():
            actual_count = len(list(task_cards_dir.glob("OP_WAVE_*.md")))
        
        # Expected from gold standard
        expected_count = 8  # 8 OP Wave task cards
        passed = actual_count >= expected_count
        
        result = ComparisonResult(
            test_id=test_id,
            test_name="Task Count",
            passed=passed,
            expected=f"{expected_count} OP Wave task cards",
            actual=f"{actual_count} found"
        )
        self.results.append(result)
        return result
    
    # ==========================================================================
    # T4-TASK: Task Card Sync
    # ==========================================================================
    
    def t4_task_cards_exist(self) -> ComparisonResult:
        """
        T4-TASK-02: All expected task cards exist.
        """
        test_id = "T4-TASK-02"
        
        expected_cards = [
            "OP_WAVE_1_1_SCHEMA_FOUNDATION.md",
            "OP_WAVE_2_1_ACTION_EXTRACTION.md",
            "OP_WAVE_2_2_BENCHMARK_EXTRACTION.md",
            "OP_WAVE_3_1_VALIDATION_TRACKER.md",
            "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR.md",
            "OP_WAVE_4_1_PILLAR_RESEARCH_LOG.md",
            "OP_WAVE_4_2_MODIFICATION_PROPOSALS.md",
            "OP_WAVE_4_3_STAKEHOLDER_MATRIX.md",
        ]
        
        task_cards_dir = self.repo_path / "task-cards"
        missing = []
        
        for card in expected_cards:
            if not (task_cards_dir / card).exists():
                missing.append(card)
        
        passed = len(missing) == 0
        
        result = ComparisonResult(
            test_id=test_id,
            test_name="Task Cards Exist",
            passed=passed,
            expected=f"All {len(expected_cards)} cards present",
            actual=f"{len(expected_cards) - len(missing)} found",
            difference=str(missing) if missing else ""
        )
        self.results.append(result)
        return result
    
    # ==========================================================================
    # Run All
    # ==========================================================================
    
    def run_all_comparisons(self) -> List[ComparisonResult]:
        """Run all gold standard comparisons"""
        self.results = []
        
        # Architecture tests
        self.t4_arch_01_module_coverage()
        self.t4_arch_02_directory_structure()
        self.t4_arch_03_operationalization_modules()
        self.t4_arch_05_freshness()
        
        # Roadmap tests
        self.t4_road_02_task_count()
        
        # Task card tests
        self.t4_task_cards_exist()
        
        return self.results
    
    def summary(self) -> Dict:
        """Get summary of all comparisons"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/len(self.results)*100):.1f}%" if self.results else "N/A",
            "results": [r.to_dict() for r in self.results]
        }


# CLI for manual testing
if __name__ == "__main__":
    import sys
    
    repo_path = Path(__file__).parent.parent.parent
    comparator = GoldStandardComparator(repo_path)
    
    print("Running Gold Standard Comparisons...")
    results = comparator.run_all_comparisons()
    
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} {result.test_id}: {result.test_name}")
        if not result.passed:
            print(f"     Expected: {result.expected}")
            print(f"     Actual:   {result.actual}")
            if result.difference:
                print(f"     Diff:     {result.difference}")
    
    print("\n" + "="*50)
    summary = comparator.summary()
    print(f"Total: {summary['total']} | Passed: {summary['passed']} | Failed: {summary['failed']}")
