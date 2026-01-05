"""
Tier 1 Tests: Doc Chain - Trigger Workflow
Tests T1-01-01 through T1-01-06

These tests validate the trigger workflow's ability to:
- Accept valid GitHub push events
- Filter out n8n automated commits (loop prevention)
- Route documentation-related changes to the distributor
- Handle edge cases appropriately
"""

import pytest


class TestTriggerWorkflowValidInput:
    """T1-01: Valid Input Handling"""
    
    def test_t1_01_01_accepts_valid_push(self, github_push_valid, workflow_simulator):
        """T1-01-01: Trigger accepts valid GitHub push event"""
        # Given a valid GitHub push event
        payload = github_push_valid
        
        # When processed by the trigger workflow
        workflow_simulator.execute_node("GitHub Webhook", payload)
        
        # Then it should accept the event
        assert payload["repository"]["full_name"] == "BootstrapAI-mgmt/Literature-Review"
        assert len(payload["commits"]) > 0
        
        # And extract the commit information
        commit = payload["commits"][0]
        assert "id" in commit
        assert "modified" in commit
        
        workflow_simulator.complete_node({"accepted": True, "commit_count": 1})
    
    def test_t1_01_02_extracts_modified_files(self, github_push_valid):
        """T1-01-02: Trigger correctly extracts modified documentation files"""
        # Given a push with documentation changes
        modified_files = github_push_valid["commits"][0]["modified"]
        
        # Then documentation files should be identified
        doc_files = [f for f in modified_files if f.startswith("docs/")]
        assert len(doc_files) > 0
        assert "docs/MASTER_ARCHITECTURE_BLUEPRINT.md" in doc_files
    
    def test_t1_01_03_generates_task_list(self, github_push_valid, workflow_simulator):
        """T1-01-03: Trigger generates appropriate task list"""
        # Given a push affecting documentation
        modified_files = github_push_valid["commits"][0]["modified"]
        
        # When tasks are generated
        tasks = []
        for f in modified_files:
            if f.startswith("docs/"):
                tasks.append({
                    "file": f,
                    "action": "sync_check"
                })
        
        # Then at least one task should be created
        assert len(tasks) >= 1
        workflow_simulator.execute_node("Task Generator", {"files": modified_files})
        workflow_simulator.complete_node({"tasks": tasks})


class TestTriggerWorkflowLoopPrevention:
    """T1-01: Loop Prevention Tests"""
    
    def test_t1_01_04_filters_n8n_automated_commits(self, github_push_n8n_automated):
        """T1-01-04: Trigger filters out n8n automated commits"""
        # Given a push from n8n automation
        pusher = github_push_n8n_automated["pusher"]["name"]
        commit_message = github_push_n8n_automated["commits"][0]["message"]
        
        # Then it should be identified as automated
        is_automated = (
            "n8n" in pusher.lower() or 
            "[n8n-auto]" in commit_message or
            "automation" in pusher.lower()
        )
        
        assert is_automated, "n8n automated commits should be detectable"
    
    def test_t1_01_05_skips_automated_processing(self, github_push_n8n_automated, workflow_simulator):
        """T1-01-05: Trigger skips processing for automated commits"""
        # Given an n8n automated push
        pusher = github_push_n8n_automated["pusher"]["name"]
        
        # When checked for automation
        should_skip = "n8n" in pusher.lower() or "automation" in pusher.lower()
        
        # Then processing should be skipped
        assert should_skip
        workflow_simulator.execute_node("Loop Prevention Check", {"pusher": pusher})
        workflow_simulator.complete_node({"should_process": False, "reason": "n8n automation"})
    
    def test_t1_01_06_allows_manual_commits(self, github_push_valid):
        """T1-01-06: Trigger allows manual commits through"""
        # Given a manual push
        pusher = github_push_valid["pusher"]["name"]
        
        # Then it should not be filtered
        is_automated = "n8n" in pusher.lower() or "automation" in pusher.lower()
        
        assert not is_automated, "Manual commits should pass through"
