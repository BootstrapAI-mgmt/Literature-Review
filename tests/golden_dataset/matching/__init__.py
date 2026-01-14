"""
Claim Matching Module

Tools for matching extracted claims to ground truth for validation.
"""

from .claim_matcher import ClaimMatcher, MatchResult

__all__ = ["ClaimMatcher", "MatchResult"]
