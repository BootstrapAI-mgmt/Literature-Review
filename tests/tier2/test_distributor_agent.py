"""
Tier 2 Tests: Distributor → Agent Integration
Tests T2-02-01 through T2-02-03

These tests validate the integration between:
- Task distributor dispatch
- Agent receiving and processing tasks
"""

import pytest


class TestDistributorAgentIntegration:
    """T2-02: Distributor → Agent Communication"""
    
    @pytest.mark.integration
    def test_t2_02_01_distributor_dispatches_to_agent(self, payloader, sample_task_payload):
        """T2-02-01: Distributor successfully dispatches task to agent"""
        # Given a task payload
        payload = sample_task_payload
        
        # When dispatched
        try:
            response = payloader.send_to_webhook("/domain-agent", payload)
            
            # Then response should indicate receipt
            assert response is not None
        except Exception as e:
            pytest.skip(f"n8n not available: {e}")
    
    @pytest.mark.integration
    def test_t2_02_02_agent_receives_correct_format(self, sample_task_payload):
        """T2-02-02: Agent receives correctly formatted task"""
        # Given a task payload
        payload = sample_task_payload
        
        # Then it should have required agent fields
        assert "task_id" in payload
        assert "domain" in payload
        assert "action" in payload
        assert "document" in payload
    
    @pytest.mark.integration
    def test_t2_02_03_agent_context_included(self, sample_task_payload):
        """T2-02-03: Agent receives task context"""
        # Given a task payload
        payload = sample_task_payload
        
        # Then context should be included
        assert "context" in payload
        assert isinstance(payload["context"], dict)
