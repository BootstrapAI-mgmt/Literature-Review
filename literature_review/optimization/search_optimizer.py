"""ROI-Optimized Search Strategy."""

import json
from typing import Dict, List, Optional
from datetime import datetime
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


class AdaptiveSearchOptimizer(SearchOptimizer):
    """Search optimizer with dynamic priority adjustment."""
    
    def __init__(self, gap_analysis_file: str, suggested_searches_file: str, config: Optional[Dict] = None):
        super().__init__(gap_analysis_file, suggested_searches_file)
        self.config = config or {}
        
        # Configuration parameters
        roi_config = self.config.get('roi_optimizer', {})
        self.recalculation_frequency = roi_config.get('recalculation_frequency', 'per_batch')
        self.batch_size = roi_config.get('batch_size', 5)
        self.min_roi_threshold = roi_config.get('min_roi_threshold', 0.1)
        self.convergence_threshold = roi_config.get('convergence_threshold', 0.8)
        
        # State tracking
        self.roi_history = []  # Track ROI changes over time
        self.gaps_state = []  # Current gap state with coverage info
    
    def optimize_searches_adaptive(self, mock_execute_batch=None) -> Dict:
        """Run searches with adaptive ROI recalculation.
        
        Args:
            mock_execute_batch: Optional function to mock search execution for testing
        
        Returns:
            Dict with completed searches, results, ROI history, and convergence info
        """
        # Initial prioritization
        initial_plan = self.optimize_search_plan()
        prioritized_searches = initial_plan['search_plan']
        
        # Initialize gaps state
        self._initialize_gaps_state()
        
        completed_searches = []
        search_results = []
        
        while prioritized_searches:
            # Execute next batch (top N searches)
            current_batch = prioritized_searches[:self.batch_size]
            
            # Run batch (use mock if provided, otherwise this would call actual search)
            if mock_execute_batch:
                batch_results = mock_execute_batch(current_batch)
            else:
                # In production, this would execute actual searches
                batch_results = self._execute_search_batch(current_batch)
            
            search_results.extend(batch_results)
            completed_searches.extend(current_batch)
            
            # Update gaps with new papers found
            self._update_gaps_with_results(batch_results)
            
            # Remove completed searches from queue
            prioritized_searches = prioritized_searches[self.batch_size:]
            
            # Recalculate ROI for remaining searches
            if prioritized_searches:
                prioritized_searches = self._recalculate_and_reorder(
                    prioritized_searches,
                    len(completed_searches)
                )
                
                # Log ROI adjustment
                self._log_roi_adjustment(prioritized_searches)
                
                # Check convergence
                if self._check_convergence():
                    logger.info("Convergence reached. Stopping search.")
                    break
                
                # Check diminishing returns
                if self._check_diminishing_returns(prioritized_searches):
                    logger.info("Diminishing returns detected. Stopping search.")
                    break
        
        return {
            'completed_searches': completed_searches,
            'search_results': search_results,
            'roi_history': self.roi_history,
            'gaps_final_coverage': self._calculate_gap_coverage(),
            'convergence_reached': self._check_convergence()
        }
    
    def _initialize_gaps_state(self):
        """Initialize gaps state from gap data."""
        self.gaps_state = []
        
        for pillar_name, pillar_data in self.gap_data.items():
            for req_name, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_name, sub_req_data in req_data.items():
                    papers_found = len(sub_req_data.get('contributing_papers', []))
                    completeness = sub_req_data.get('completeness_percent', 0)
                    
                    # Create gap entry
                    gap_id = f"{pillar_name}::{req_name}::{sub_req_name}"
                    self.gaps_state.append({
                        'id': gap_id,
                        'pillar': pillar_name,
                        'requirement': sub_req_name,
                        'base_severity': self._completeness_to_severity_score(completeness),
                        'current_coverage': completeness / 100.0,
                        'evidence_papers': sub_req_data.get('contributing_papers', []).copy()
                    })
    
    def _completeness_to_severity_score(self, completeness: float) -> float:
        """Convert completeness percentage to numeric severity score."""
        if completeness == 0:
            return 9.0  # Critical
        elif completeness < 30:
            return 7.0  # High
        elif completeness < 70:
            return 5.0  # Medium
        elif completeness < 90:
            return 3.0  # Low
        else:
            return 1.0  # Covered
    
    def _execute_search_batch(self, batch: List[Dict]) -> List[Dict]:
        """Execute a batch of searches (placeholder for production implementation)."""
        # In production, this would call actual search APIs
        # For now, return empty results
        return [{'search': s, 'papers': [], 'target_gap_ids': []} for s in batch]
    
    def _update_gaps_with_results(self, search_results: List[Dict]):
        """Update gap coverage based on new papers found."""
        for result in search_results:
            papers = result.get('papers', [])
            search_info = result.get('search', {})
            
            # Find matching gap based on requirement
            requirement = search_info.get('requirement', '')
            
            for gap in self.gaps_state:
                if requirement in gap['requirement']:
                    # Add papers to gap's evidence
                    gap['evidence_papers'].extend(papers)
                    
                    # Recalculate coverage (simplified - count unique papers)
                    unique_papers = len(set([p.get('title', p.get('filename', str(i))) 
                                            for i, p in enumerate(gap['evidence_papers'])]))
                    # Update coverage: more papers = higher coverage, max at 8 papers
                    gap['current_coverage'] = min(unique_papers / 8.0, 1.0)
    
    def _recalculate_and_reorder(self, pending_searches: List[Dict], completed_count: int) -> List[Dict]:
        """Recalculate ROI for pending searches and reorder."""
        # Recalculate ROI for each pending search
        for search in pending_searches:
            # Find target gap
            requirement = search.get('requirement', '')
            target_gap = next((g for g in self.gaps_state if requirement in g['requirement']), None)
            
            if not target_gap:
                search['roi'] = search['roi_score']  # Keep original
                continue
            
            # Skip if gap fully covered
            if target_gap.get('current_coverage', 0) > 0.95:
                search['roi'] = 0.0
                search['skip_reason'] = 'gap_covered'
                continue
            
            # Recalculate severity based on current coverage
            old_roi = search['roi_score']
            current_severity = self._recalculate_severity(target_gap)
            
            # Calculate new ROI
            papers_needed = max(0, 8 - len(target_gap.get('evidence_papers', [])))
            papers_score = min(papers_needed / 5.0, 1.0)
            
            # Estimate query specificity
            query = search.get('query', '')
            specificity = 0.5
            if ' and ' in query.lower() or '"' in query:
                specificity = 0.8
            if len(query.split()) > 5:
                specificity = 0.9
            
            new_roi = current_severity * papers_score * specificity
            search['roi'] = round(new_roi, 2)
            search['roi_delta'] = round(new_roi - old_roi, 2)
        
        # Filter out zero-ROI searches
        pending_searches = [s for s in pending_searches if s.get('roi', 0) > 0]
        
        # Re-sort by ROI
        pending_searches.sort(key=lambda x: x.get('roi', 0), reverse=True)
        
        # Record in history
        self.roi_history.append({
            'timestamp': datetime.now().isoformat(),
            'completed_count': completed_count,
            'pending_count': len(pending_searches),
            'avg_roi': sum([s.get('roi', 0) for s in pending_searches]) / len(pending_searches) if pending_searches else 0,
            'top_search_roi': pending_searches[0].get('roi', 0) if pending_searches else 0
        })
        
        return pending_searches
    
    def _recalculate_severity(self, gap: Dict) -> float:
        """Recalculate gap severity based on current coverage."""
        base_severity = gap.get('base_severity', 5.0)
        current_coverage = gap.get('current_coverage', 0.0)
        
        # Reduce severity as coverage improves
        # Severity drops exponentially: fully covered gap = 0 severity
        adjusted_severity = base_severity * (1 - current_coverage)
        
        return adjusted_severity
    
    def _calculate_gap_coverage(self) -> List[Dict]:
        """Calculate current coverage for all gaps."""
        return [{
            'gap_id': gap['id'],
            'requirement': gap['requirement'],
            'coverage': gap.get('current_coverage', 0),
            'papers_count': len(gap.get('evidence_papers', []))
        } for gap in self.gaps_state]
    
    def _check_convergence(self) -> bool:
        """Check if convergence criteria met."""
        # Find critical gaps (base_severity >= 7)
        critical_gaps = [g for g in self.gaps_state if g.get('base_severity', 0) >= 7]
        
        if not critical_gaps:
            return True  # No critical gaps
        
        # Check if all critical gaps are sufficiently covered
        covered_critical = [g for g in critical_gaps if g.get('current_coverage', 0) >= self.convergence_threshold]
        
        return len(covered_critical) == len(critical_gaps)
    
    def _check_diminishing_returns(self, pending_searches: List[Dict]) -> bool:
        """Check if next search has diminishing returns."""
        if not pending_searches:
            return True
        
        # Check if top search ROI below threshold
        top_roi = pending_searches[0].get('roi', 0)
        
        return top_roi < self.min_roi_threshold
    
    def _log_roi_adjustment(self, searches: List[Dict]):
        """Log ROI adjustments for debugging."""
        logger.info("\n=== ROI Recalculation ===")
        logger.info(f"Pending Searches: {len(searches)}")
        
        if searches:
            logger.info("Top 3 searches by ROI:")
            for i, search in enumerate(searches[:3]):
                delta_str = f" (Δ{search.get('roi_delta', 0):+.2f})" if 'roi_delta' in search else ""
                logger.info(f"  {i+1}. {search.get('query', 'N/A')} - ROI: {search.get('roi', 0):.2f}{delta_str}")


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
