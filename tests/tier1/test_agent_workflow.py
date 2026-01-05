"""
Tier 1 Tests: Doc Chain - Agent Workflow
Tests T1-03-01 through T1-03-06

These tests validate the agent workflow's ability to:
- Receive tasks from distributor
- Execute documentation operations
- Return results via callback
- Handle failures appropriately
"""

import pytest


class TestAgentWorkflowTaskReceipt:
    """T1-03: Task Receipt Tests"""
    
    def test_t1_03_01_receives_task_payload(self, agent_task_payload):
        """T1-03-01: Agent receives task payload from distributor"""
        payload = agent_task_payload
        
        assert "task_id" in payload
        assert "domain" in payload
        assert payload["domain"] == "documentation"
    
    def test_t1_03_02_validates_task_instructions(self, agent_task_payload):
        """T1-03-02: Agent validates task instructions"""
        payload = agent_task_payload
        
        assert "instructions" in payload
        assert "operation" in payload["instructions"]
        assert payload["instructions"]["operation"] == "ensure_modules_documented"
    
    def test_t1_03_03_extracts_context(self, agent_task_payload):
        """T1-03-03: Agent extracts execution context"""
        payload = agent_task_payload
        
        assert "context" in payload
        assert "changed_files" in payload["context"]
        assert len(payload["context"]["changed_files"]) > 0


class TestAgentWorkflowExecution:
    """T1-03: Execution and Callback Tests"""
    
    def test_t1_03_04_success_callback_structure(self, agent_callback_success):
        """T1-03-04: Agent success callback has correct structure"""
        callback = agent_callback_success
        
        assert callback["status"] == "success"
        assert "result" in callback
        assert "changes_made" in callback["result"]
    
    def test_t1_03_05_failure_callback_structure(self, agent_callback_failure):
        """T1-03-05: Agent failure callback has error details"""
        callback = agent_callback_failure
        
        assert callback["status"] == "failure"
        assert "error" in callback
        assert "type" in callback["error"]
        assert "message" in callback["error"]
    
    def test_t1_03_06_includes_metrics(self, agent_callback_success, agent_callback_failure):
        """T1-03-06: Agent callbacks include execution metrics"""
        for callback in [agent_callback_success, agent_callback_failure]:
            assert "metrics" in callback
            assert "execution_time_ms" in callback["metrics"]
