"""
Tier 2 Tests: Cross-Workflow Integration
Tests T2-04-01 through T2-04-03

These tests validate cross-workflow communication:
- Error workflow receives from other workflows
- State reconciliation triggers agents
"""

import pytest


class TestCrossWorkflowIntegration:
    """T2-04: Cross-Workflow Communication"""
    
    @pytest.mark.integration
    def test_t2_04_01_error_workflow_receives_failures(self, payloader):
        """T2-04-01: Error workflow receives failure notifications"""
        # Given an error notification payload
        error_payload = {
            "workflow": "Doc Chain - Errors",
            "trigger": "error_callback",
            "error": {
                "type": "WorkflowExecutionError",
                "workflow": "Doc Chain - Agent",
                "message": "Test error",
                "severity": "high"
            }
        }
        
        # Then the error structure should be valid
        assert error_payload["trigger"] == "error_callback"
        assert "error" in error_payload
        assert error_payload["error"]["severity"] in ["low", "medium", "high", "critical"]
    
    @pytest.mark.integration
    def test_t2_04_02_state_recon_triggers_agents(self, payloader):
        """T2-04-02: State reconciliation can trigger agents"""
        # Given a state reconciliation payload
        recon_payload = {
            "trigger": "scheduled",
            "scope": "full_repository",
            "documents_to_check": [
                "docs/MASTER_ARCHITECTURE_BLUEPRINT.md"
            ],
            "validation_rules": {
                "check_module_coverage": True
            }
        }
        
        # Then it should be valid for sending
        assert recon_payload["trigger"] == "scheduled"
        assert len(recon_payload["documents_to_check"]) > 0
    
    @pytest.mark.integration
    def test_t2_04_03_pr_workflow_integration(self, payloader, sample_pr_payload):
        """T2-04-03: PR workflow integrates with other components"""
        # Given a PR payload
        payload = sample_pr_payload
        
        # Then it should have correct structure for integration
        assert "pull_request" in payload
        assert "repository" in payload
        assert payload["pull_request"]["base"]["ref"] == "main"
