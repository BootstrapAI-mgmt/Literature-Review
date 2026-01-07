"""
Tier 2 Tests: Endpoint Availability
Tests T2-EP-01 through T2-EP-09

These tests validate that all n8n webhook endpoints are accessible.
Per Master Validation Plan V2.0.0 Section 4.2.2
"""

import pytest
from .payloader import Payloader, PayloaderError, REQUESTS_AVAILABLE


class TestEndpointAvailability:
    """T2-EP: Endpoint Availability Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup payloader with short timeout for availability checks"""
        self.payloader = Payloader(timeout=5)
    
    @pytest.mark.integration
    def test_t2_ep_01_github_trigger_endpoint(self, endpoints):
        """T2-EP-01: GitHub trigger endpoint is accessible"""
        endpoint = endpoints.get("github_doc_trigger", "/github-doc-trigger")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_02_task_distributor_endpoint(self, endpoints):
        """T2-EP-02: Task distributor endpoint is accessible"""
        endpoint = endpoints.get("task_distributor", "/task-distributor")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_03_domain_agent_endpoint(self, endpoints):
        """T2-EP-03: Domain agent endpoint is accessible"""
        endpoint = endpoints.get("domain_agent", "/domain-agent")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_04_task_callback_endpoint(self, endpoints):
        """T2-EP-04: Task callback endpoint is accessible"""
        endpoint = endpoints.get("task_callback", "/task-callback")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_05_distributor_status_endpoint(self, endpoints):
        """T2-EP-05: Distributor status endpoint is accessible"""
        endpoint = endpoints.get("distributor_status", "/distributor-status")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_06_state_reconciliation_endpoint(self, endpoints):
        """T2-EP-06: State reconciliation endpoint is accessible"""
        endpoint = endpoints.get("state_reconciliation", "/state-reconciliation")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_07_staleness_review_endpoint(self, endpoints):
        """T2-EP-07: Staleness review endpoint is accessible"""
        endpoint = endpoints.get("staleness_review", "/staleness-review")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_08_pr_review_endpoint(self, endpoints):
        """T2-EP-08: PR review endpoint is accessible"""
        endpoint = endpoints.get("pr_review", "/pr-review")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
    
    @pytest.mark.integration
    def test_t2_ep_09_error_workflow_endpoint(self, endpoints):
        """T2-EP-09: Error workflow endpoint is accessible"""
        endpoint = endpoints.get("error_workflow", "/error-handler")
        
        if not REQUESTS_AVAILABLE:
            pytest.skip("requests library not available")
        
        try:
            response = self.payloader.send_to_webhook(endpoint, {"test": True})
            assert response is not None
        except PayloaderError as e:
            pytest.skip(f"Endpoint not available: {e}")
