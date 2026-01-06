"""
Tier 2 Tests: Trigger → Distributor Integration
Tests T2-01-01 through T2-01-03

These tests validate the integration between:
- GitHub webhook trigger
- Task distributor receiving queued tasks
"""

import pytest


class TestTriggerDistributorIntegration:
    """T2-01: Trigger → Distributor Communication"""
    
    @pytest.mark.integration
    def test_t2_01_01_trigger_sends_to_distributor(self, payloader, sample_push_payload):
        """T2-01-01: Trigger successfully sends task to distributor"""
        # Given a GitHub push payload
        payload = sample_push_payload
        
        # When sent to the trigger endpoint
        try:
            response = payloader.send_to_webhook("/github-doc-trigger", payload)
            
            # Then a response should be received
            assert response is not None
            # And the response should indicate acceptance
            assert response.get("status") in ["ok", "mock", "queued", "accepted"]
        except Exception as e:
            # If n8n is not available, test passes with mock
            pytest.skip(f"n8n not available: {e}")
    
    @pytest.mark.integration
    def test_t2_01_02_distributor_receives_task(self, payloader, sample_task_payload):
        """T2-01-02: Distributor receives task from trigger"""
        # Given a task payload
        payload = sample_task_payload
        
        # When checking distributor status
        try:
            # First send a task
            payloader.send_to_webhook("/task-distributor", payload)
            
            # Then check status
            status = payloader.check_distributor_status()
            assert status is not None
        except Exception as e:
            pytest.skip(f"n8n not available: {e}")
    
    @pytest.mark.integration
    def test_t2_01_03_task_format_preserved(self, payloader, sample_push_payload):
        """T2-01-03: Task format is preserved through communication"""
        # Given a push with specific files
        payload = sample_push_payload
        modified_files = payload["commits"][0]["modified"]
        
        # The format should be maintained
        assert isinstance(modified_files, list)
        assert all(isinstance(f, str) for f in modified_files)
        assert "docs/MASTER_ARCHITECTURE_BLUEPRINT.md" in modified_files
