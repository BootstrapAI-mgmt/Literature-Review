"""Unit tests for Judge consensus review functions."""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.judge import should_trigger_consensus, trigger_consensus_review


class TestConsensusReview:
    """Test consensus review triggering logic."""
    
    def test_should_trigger_consensus_for_borderline_low(self):
        """Test consensus triggers for low borderline score (2.5)."""
        claim = {
            'claim_id': 'test_001',
            'evidence_quality': {
                'composite_score': 2.5
            }
        }
        assert should_trigger_consensus(claim) is True
    
    def test_should_trigger_consensus_for_borderline_mid(self):
        """Test consensus triggers for mid borderline score (3.0)."""
        claim = {
            'claim_id': 'test_002',
            'evidence_quality': {
                'composite_score': 3.0
            }
        }
        assert should_trigger_consensus(claim) is True
    
    def test_should_trigger_consensus_for_borderline_high(self):
        """Test consensus triggers for high borderline score (3.5)."""
        claim = {
            'claim_id': 'test_003',
            'evidence_quality': {
                'composite_score': 3.5
            }
        }
        assert should_trigger_consensus(claim) is True
    
    def test_should_not_trigger_consensus_for_low_score(self):
        """Test consensus does not trigger for low score (< 2.5)."""
        claim = {
            'claim_id': 'test_004',
            'evidence_quality': {
                'composite_score': 2.4
            }
        }
        assert should_trigger_consensus(claim) is False
    
    def test_should_not_trigger_consensus_for_high_score(self):
        """Test consensus does not trigger for high score (> 3.5)."""
        claim = {
            'claim_id': 'test_005',
            'evidence_quality': {
                'composite_score': 3.6
            }
        }
        assert should_trigger_consensus(claim) is False
    
    def test_should_not_trigger_consensus_for_missing_quality(self):
        """Test consensus does not trigger when evidence_quality is missing."""
        claim = {
            'claim_id': 'test_006'
        }
        assert should_trigger_consensus(claim) is False
    
    def test_should_not_trigger_consensus_for_missing_composite(self):
        """Test consensus does not trigger when composite_score is missing."""
        claim = {
            'claim_id': 'test_007',
            'evidence_quality': {}
        }
        assert should_trigger_consensus(claim) is False
    
    def test_trigger_consensus_review_adds_metadata(self):
        """Test that trigger_consensus_review adds correct metadata."""
        claim = {
            'claim_id': 'test_008',
            'evidence_quality': {
                'composite_score': 2.8
            }
        }
        
        result = trigger_consensus_review(claim)
        
        assert 'consensus_review' in result
        assert result['consensus_review']['triggered'] is True
        assert result['consensus_review']['reason'] == 'borderline_composite_score'
        assert result['consensus_review']['composite_score'] == 2.8
        assert 'consensus_reviewers' in result['consensus_review']
        assert len(result['consensus_review']['consensus_reviewers']) >= 2
        assert 'timestamp' in result['consensus_review']
        assert result['consensus_review']['status'] == 'pending'
    
    def test_trigger_consensus_review_preserves_original_claim(self):
        """Test that trigger_consensus_review preserves original claim data."""
        claim = {
            'claim_id': 'test_009',
            'pillar': 'Pillar 1',
            'sub_requirement': 'SR 1.1',
            'evidence_quality': {
                'composite_score': 3.2,
                'strength_score': 3
            }
        }
        
        original_claim_id = claim['claim_id']
        original_pillar = claim['pillar']
        
        result = trigger_consensus_review(claim)
        
        # Original data should be preserved
        assert result['claim_id'] == original_claim_id
        assert result['pillar'] == original_pillar
        assert result['evidence_quality']['strength_score'] == 3
