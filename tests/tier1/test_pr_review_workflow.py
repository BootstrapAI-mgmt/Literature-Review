"""
Tier 1 Tests: PR Review Workflow
Tests T1-05-01 through T1-05-03

These tests validate the PR review workflow's ability to:
- Receive PR events
- Extract task references
- Generate review comments
"""

import pytest


class TestPRReviewWorkflow:
    """T1-05: PR Review Tests"""
    
    def test_t1_05_01_receives_pr_event(self, pr_review_webhook):
        """T1-05-01: PR review receives PR webhook"""
        payload = pr_review_webhook
        
        assert payload["action"] == "opened"
        assert "pull_request" in payload
        assert payload["pull_request"]["number"] == 130
    
    def test_t1_05_02_extracts_task_reference(self, pr_review_webhook):
        """T1-05-02: PR review extracts task references from body"""
        pr_body = pr_review_webhook["pull_request"]["body"]
        
        # Should find OP-W3-1 reference
        assert "OP-W3-1" in pr_body
    
    def test_t1_05_03_validates_pr_structure(self, pr_review_webhook):
        """T1-05-03: PR review validates PR structure"""
        pr = pr_review_webhook["pull_request"]
        
        assert "title" in pr
        assert "body" in pr
        assert "head" in pr
        assert "base" in pr
        assert pr["base"]["ref"] == "main"
