"""
Tier 1 Tests: Staleness Workflow
Tests T1-08-01 through T1-08-04

These tests validate the staleness workflow's ability to:
- Check document freshness
- Apply thresholds correctly
- Identify stale documents
"""

import pytest


class TestStalenessWorkflow:
    """T1-08: Staleness Workflow Tests"""
    
    def test_t1_08_01_validates_trigger(self, staleness_review):
        """T1-08-01: Staleness workflow validates scheduled trigger"""
        payload = staleness_review
        
        assert payload["trigger"] == "scheduled"
        assert payload["scope"] == "all_documents"
    
    def test_t1_08_02_applies_thresholds(self, staleness_review):
        """T1-08-02: Staleness workflow applies correct thresholds"""
        thresholds = staleness_review["thresholds"]
        
        assert thresholds["master_documents"] == 7
        assert thresholds["task_cards"] == 3
        assert thresholds["wave_indexes"] == 1
    
    def test_t1_08_03_evaluates_document_status(self, staleness_review):
        """T1-08-03: Staleness workflow evaluates each document"""
        docs = staleness_review["documents_checked"]
        
        for doc in docs:
            assert "path" in doc
            assert "age_days" in doc
            assert "threshold_days" in doc
            assert "status" in doc
            assert doc["status"] in ["fresh", "stale", "warning"]
    
    def test_t1_08_04_reports_no_action_needed(self, staleness_review):
        """T1-08-04: Staleness workflow reports when no action needed"""
        payload = staleness_review
        
        # When stale_documents is empty
        assert len(payload["stale_documents"]) == 0
        # Then action_required should be False
        assert payload["action_required"] == False
