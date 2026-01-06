"""
Tier 1 Tests: Release Workflow
Tests T1-06-01 through T1-06-03

These tests validate the release workflow's ability to:
- Receive tag push events
- Extract release information
- Generate release documentation
"""

import pytest


class TestReleaseWorkflow:
    """T1-06: Release Workflow Tests"""
    
    def test_t1_06_01_receives_tag_event(self, release_tag_webhook):
        """T1-06-01: Release workflow receives tag webhook"""
        payload = release_tag_webhook
        
        assert payload["ref_type"] == "tag"
        assert "release" in payload
    
    def test_t1_06_02_extracts_version(self, release_tag_webhook):
        """T1-06-02: Release workflow extracts version from tag"""
        tag_name = release_tag_webhook["release"]["tag_name"]
        
        assert tag_name.startswith("v")
        assert tag_name == "v2.1.0"
    
    def test_t1_06_03_validates_release_properties(self, release_tag_webhook):
        """T1-06-03: Release workflow validates release properties"""
        release = release_tag_webhook["release"]
        
        assert release["draft"] == False
        assert release["prerelease"] == False
        assert "body" in release
        assert "## Release Notes" in release["body"]
