"""
Claim Matching Utilities

Tools for matching extracted claims to golden dataset claims.
"""

from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re


class ClaimMatcher:
    """
    Match extracted claims to golden dataset claims.
    
    Uses text similarity and pillar/requirement matching.
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize matcher.
        
        Args:
            similarity_threshold: Minimum similarity for a match (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove punctuation (except numbers)
        text = re.sub(r'[^\w\s\d]', '', text)
        return text
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity ratio."""
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def find_best_match(
        self,
        extracted_claim: Dict,
        golden_claims: List[Dict],
        require_pillar_match: bool = True
    ) -> Optional[Tuple[str, float]]:
        """
        Find the best matching golden claim for an extracted claim.
        
        Args:
            extracted_claim: The extracted claim to match
            golden_claims: List of golden dataset claims
            require_pillar_match: If True, only consider same-pillar claims
        
        Returns:
            Tuple of (golden_claim_id, similarity_score) or None
        """
        best_match = None
        best_score = 0.0
        
        extracted_text = extracted_claim.get("claim_text", "")
        extracted_pillar = extracted_claim.get("pillar", "")
        
        for golden in golden_claims:
            # Filter by pillar if required
            if require_pillar_match:
                golden_pillar = golden.get("correct_pillar", "")
                if not self._pillars_match(extracted_pillar, golden_pillar):
                    continue
            
            # Calculate text similarity
            golden_text = golden.get("claim_text", "")
            similarity = self.calculate_similarity(extracted_text, golden_text)
            
            # Also check evidence text for partial matches
            evidence_text = golden.get("evidence_text", "")
            evidence_similarity = self.calculate_similarity(extracted_text, evidence_text)
            
            # Use the higher similarity
            final_similarity = max(similarity, evidence_similarity * 0.8)
            
            if final_similarity > best_score:
                best_score = final_similarity
                best_match = golden.get("claim_id")
        
        if best_score >= self.similarity_threshold:
            return (best_match, best_score)
        
        return None
    
    def _pillars_match(self, pillar1: str, pillar2: str) -> bool:
        """Check if two pillar names match (allowing partial matching)."""
        # Extract pillar number if present
        p1_match = re.search(r'pillar\s*(\d+)', pillar1.lower())
        p2_match = re.search(r'pillar\s*(\d+)', pillar2.lower())
        
        if p1_match and p2_match:
            return p1_match.group(1) == p2_match.group(1)
        
        # Fallback to substring matching
        return pillar1.lower() in pillar2.lower() or pillar2.lower() in pillar1.lower()
    
    def match_all(
        self,
        extracted_claims: List[Dict],
        golden_claims: List[Dict]
    ) -> Dict[str, any]:
        """
        Match all extracted claims to golden claims.
        
        Returns:
            Dictionary with matches, true positives, false positives, etc.
        """
        matches = []
        unmatched_extracted = []
        matched_golden_ids = set()
        
        for extracted in extracted_claims:
            match = self.find_best_match(extracted, golden_claims)
            
            if match:
                golden_id, score = match
                matches.append({
                    "extracted_id": extracted.get("claim_id"),
                    "golden_id": golden_id,
                    "similarity": score
                })
                matched_golden_ids.add(golden_id)
            else:
                unmatched_extracted.append(extracted)
        
        # Find unmatched golden claims (false negatives)
        all_golden_ids = {g.get("claim_id") for g in golden_claims}
        missed_golden = all_golden_ids - matched_golden_ids
        
        return {
            "matches": matches,
            "true_positives": len(matches),
            "false_positives": len(unmatched_extracted),
            "false_negatives": len(missed_golden),
            "unmatched_extracted": unmatched_extracted,
            "missed_golden_ids": list(missed_golden)
        }
