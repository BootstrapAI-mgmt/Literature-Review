"""ROI-Optimized Search Strategy."""

import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class SearchOptimizer:
    """Optimize search strategy based on gap analysis."""
    
    def __init__(self, gap_analysis_file: str, suggested_searches_file: str):
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
        with open(suggested_searches_file, 'r') as f:
            self.searches = json.load(f)
    
    def optimize_search_plan(self) -> Dict:
        """Generate optimized search plan."""
        logger.info("Optimizing search strategy...")
        
        # Score each search query
        scored_searches = []
        
        for search_entry in self.searches:
            requirement = search_entry.get('requirement')
            pillar = search_entry.get('pillar')
            
            # Get gap info
            gap_info = self._get_gap_info(requirement, pillar)
            
            if not gap_info:
                continue
            
            # Process each suggested search query
            for query_data in search_entry.get('suggested_searches', []):
                query = query_data.get('query', '')
                
                # Calculate ROI score
                roi_score = self._calculate_search_roi(query, gap_info)
                
                scored_searches.append({
                    'query': query,
                    'requirement': requirement,
                    'pillar': pillar,
                    'roi_score': roi_score,
                    'gap_severity': gap_info['gap_severity'],
                    'papers_needed': gap_info['papers_needed'],
                    'priority': self._assign_priority(roi_score)
                })
        
        # Sort by ROI
        scored_searches.sort(key=lambda x: x['roi_score'], reverse=True)
        
        return {
            'total_searches': len(scored_searches),
            'high_priority_searches': len([s for s in scored_searches if s['priority'] == 'HIGH']),
            'search_plan': scored_searches,
            'execution_order': [s['query'] for s in scored_searches[:20]]  # Top 20
        }
    
    def _get_gap_info(self, requirement: str, pillar_short: str) -> Dict:
        """Get gap analysis info for requirement."""
        # Map pillar short name to full name
        pillar_map = {}
        for pillar_name in self.gap_data.keys():
            # Extract pillar number (e.g., "Pillar 1" from "Pillar 1: Biological...")
            if pillar_name.startswith(pillar_short):
                pillar_map[pillar_short] = pillar_name
        
        pillar_full = pillar_map.get(pillar_short)
        if not pillar_full or pillar_full not in self.gap_data:
            return {}
        
        pillar_data = self.gap_data[pillar_full]
        
        # Search for the requirement in the analysis
        for req_name, req_data in pillar_data.get('analysis', {}).items():
            # Check sub-requirements
            for sub_req_name, sub_req_data in req_data.items():
                if sub_req_name.endswith(requirement) or requirement in sub_req_name:
                    papers_found = len(sub_req_data.get('contributing_papers', []))
                    completeness = sub_req_data.get('completeness_percent', 0)
                    papers_needed = max(0, 8 - papers_found)  # Target 8 papers
                    
                    # Determine gap severity based on completeness
                    if completeness == 0:
                        gap_severity = 'Critical'
                    elif completeness < 30:
                        gap_severity = 'High'
                    elif completeness < 70:
                        gap_severity = 'Medium'
                    elif completeness < 90:
                        gap_severity = 'Low'
                    else:
                        gap_severity = 'Covered'
                    
                    return {
                        'gap_severity': gap_severity,
                        'papers_found': papers_found,
                        'papers_needed': papers_needed,
                        'avg_alignment': completeness / 100.0
                    }
        
        return {}
    
    def _calculate_search_roi(self, query: str, gap_info: Dict) -> float:
        """Calculate ROI score for a search query."""
        # Factors:
        # 1. Gap severity (Critical = 3, High = 2, Medium = 1, Low = 0.5)
        # 2. Papers needed (more needed = higher priority)
        # 3. Query specificity (more specific = higher success rate)
        
        severity_weights = {
            'Critical': 3.0,
            'High': 2.0,
            'Medium': 1.0,
            'Low': 0.5,
            'Covered': 0.1
        }
        
        severity_score = severity_weights.get(gap_info['gap_severity'], 1.0)
        papers_score = min(gap_info['papers_needed'] / 5.0, 1.0)  # Normalize to 0-1
        
        # Query specificity (count AND operators, quotes, etc.)
        query_lower = query.lower()
        specificity = 0.5
        if ' and ' in query_lower or '"' in query:
            specificity = 0.8
        if len(query.split()) > 5:
            specificity = 0.9
        
        # Combined ROI score
        roi = severity_score * papers_score * specificity
        
        return round(roi, 2)
    
    def _assign_priority(self, roi_score: float) -> str:
        """Assign priority level."""
        if roi_score >= 2.0:
            return 'HIGH'
        elif roi_score >= 1.0:
            return 'MEDIUM'
        else:
            return 'LOW'


def generate_search_plan(gap_file: str, searches_file: str, output_file: str = 'gap_analysis_output/optimized_search_plan.json'):
    """Generate optimized search plan."""
    import os
    
    optimizer = SearchOptimizer(gap_file, searches_file)
    plan = optimizer.optimize_search_plan()
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(plan, f, indent=2)
    
    print("\n" + "="*60)
    print("OPTIMIZED SEARCH PLAN")
    print("="*60)
    print(f"\nTotal Searches: {plan['total_searches']}")
    print(f"High Priority: {plan['high_priority_searches']}")
    print(f"\nTop 10 Searches (Execute First):")
    for i, query in enumerate(plan['execution_order'][:10], 1):
        print(f"  {i}. {query}")
    print("\n" + "="*60)
    
    return plan
