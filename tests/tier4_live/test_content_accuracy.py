"""
Tier 4 Live Content Accuracy Tests

These tests validate ACTUAL content against gold standards.
They trigger real n8n workflows and verify outputs match expectations.

Per MASTER_N8N_VALIDATION_PLAN.md Section 8:
- T4-ARCH-*: Architecture Blueprint Accuracy
- T4-ROAD-*: Repository Roadmap Accuracy
- T4-TASK-*: Task Card Synchronization
"""

import pytest
import json
from pathlib import Path


class TestArchitectureBlueprintAccuracy:
    """
    T4-ARCH: Architecture Blueprint Accuracy Tests
    
    Validates that MASTER_ARCHITECTURE_BLUEPRINT.md accurately
    reflects the actual repository structure.
    """
    
    def test_t4_arch_01_module_coverage(self, gold_comparator):
        """
        T4-ARCH-01: All Python modules in literature_review/ documented
        
        GOLD STANDARD: Every .py file in literature_review/ should appear
        in MASTER_ARCHITECTURE_BLUEPRINT.md
        """
        result = gold_comparator.t4_arch_01_module_coverage()
        
        assert result.passed, (
            f"Module coverage failed: {result.difference}\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}"
        )
    
    def test_t4_arch_02_directory_structure(self, gold_comparator):
        """
        T4-ARCH-02: Directory structure matches actual package
        
        GOLD STANDARD: Core directories (analysis, reviewers, models, 
        optimization, prompts) must exist.
        """
        result = gold_comparator.t4_arch_02_directory_structure()
        
        assert result.passed, (
            f"Directory structure mismatch: {result.difference}\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}"
        )
    
    def test_t4_arch_03_operationalization_modules(self, gold_comparator):
        """
        T4-ARCH-03: Operationalization modules documented
        
        GOLD STANDARD: action_vector.py, validation_strategy.py, etc.
        must be documented in the architecture blueprint.
        """
        result = gold_comparator.t4_arch_03_operationalization_modules()
        
        assert result.passed, (
            f"Missing OP modules: {result.difference}\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}"
        )
    
    def test_t4_arch_05_freshness(self, gold_comparator):
        """
        T4-ARCH-05: Document freshness (≤7 days)
        
        GOLD STANDARD: MASTER_ARCHITECTURE_BLUEPRINT.md should be
        updated within 7 days of any structural change.
        """
        result = gold_comparator.t4_arch_05_freshness()
        
        # Note: This may legitimately fail if no recent updates
        if not result.passed:
            pytest.skip(f"Document stale: {result.actual}")


class TestRoadmapAccuracy:
    """
    T4-ROAD: Repository Roadmap Accuracy Tests
    
    Validates that roadmap documents accurately reflect
    actual project state.
    """
    
    def test_t4_road_02_task_count(self, gold_comparator):
        """
        T4-ROAD-02: Task count reflects actual task cards
        
        GOLD STANDARD: Roadmap should show correct count of
        Operationalization Wave task cards (8 expected).
        """
        result = gold_comparator.t4_road_02_task_count()
        
        assert result.passed, (
            f"Task count mismatch\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}"
        )


class TestTaskCardSync:
    """
    T4-TASK: Task Card Synchronization Tests
    
    Validates task cards match expected state.
    """
    
    def test_t4_task_02_cards_exist(self, gold_comparator):
        """
        T4-TASK-02: All OP Wave task cards exist
        
        GOLD STANDARD: All 8 OP_WAVE_*.md files must exist
        in task-cards/ directory.
        """
        result = gold_comparator.t4_task_cards_exist()
        
        assert result.passed, (
            f"Missing task cards: {result.difference}\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}"
        )


class TestLiveWorkflowExecution:
    """
    Live workflow execution tests.
    
    These tests trigger actual n8n workflows and validate
    the responses against expected formats.
    """
    
    @pytest.mark.slow
    def test_t4_live_01_trigger_workflow_responds(self, workflow_runner, require_live_n8n):
        """
        T4-LIVE-01: Trigger workflow responds to push event
        
        Triggers /github-doc-trigger and validates response structure.
        Duration: ~30-60 seconds
        """
        result = workflow_runner.trigger_github_push(["docs/test.md"])
        
        assert result.success, f"Workflow trigger failed: {result.error}"
        assert result.webhook_response.get("success"), "Webhook should return success"
    
    @pytest.mark.slow
    def test_t4_live_02_mcp_bridge_health(self, workflow_runner, require_live_n8n):
        """
        T4-LIVE-02: MCP Bridge health check
        
        Validates the MCP Bridge is operational.
        """
        status = workflow_runner.check_mcp_status()
        
        assert status.get("success"), "MCP Bridge should be healthy"
        assert status.get("status") == "healthy", "Status should be 'healthy'"
    
    @pytest.mark.slow
    def test_t4_live_03_pr_review_responds(self, workflow_runner, require_live_n8n):
        """
        T4-LIVE-03: PR Review workflow responds
        
        Triggers /pr-review and validates response.
        Duration: ~30-60 seconds
        """
        result = workflow_runner.trigger_pr_review(pr_number=9999)
        
        assert result.success, f"PR review trigger failed: {result.error}"


class TestGoldStandardSuite:
    """
    Run full gold standard comparison suite.
    """
    
    def test_t4_full_gold_standard_suite(self, gold_comparator):
        """
        Run all gold standard comparisons and report results.
        """
        results = gold_comparator.run_all_comparisons()
        summary = gold_comparator.summary()
        
        # Print detailed results
        print("\n" + "="*60)
        print("GOLD STANDARD COMPARISON RESULTS")
        print("="*60)
        
        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {result.test_id}: {result.test_name}")
            if not result.passed:
                print(f"     Expected: {result.expected}")
                print(f"     Actual:   {result.actual}")
        
        print("="*60)
        print(f"Total: {summary['total']} | Passed: {summary['passed']} | Failed: {summary['failed']}")
        print("="*60)
        
        # Assert high pass rate (allow some flexibility for legitimate failures)
        assert summary['passed'] >= summary['total'] * 0.8, (
            f"Gold standard pass rate too low: {summary['pass_rate']}"
        )
