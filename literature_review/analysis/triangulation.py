"""Evidence Triangulation Analysis - detect bias and source diversity."""

import json
from collections import defaultdict
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class TriangulationAnalyzer:
    """Analyze source diversity and evidence triangulation."""
    
    def __init__(self, review_log_file: str, gap_analysis_file: str):
        with open(review_log_file, 'r') as f:
            review_data = json.load(f)
            # Handle both list and dict formats
            if isinstance(review_data, list):
                # If it's a list of filenames, create empty dict
                self.reviews = {}
            else:
                self.reviews = review_data
        
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
    
    def analyze_triangulation(self) -> Dict:
        """Perform triangulation analysis."""
        logger.info("Analyzing evidence triangulation...")
        
        # Group papers by author/institution
        author_groups = self._group_by_authors()
        institution_groups = self._group_by_institutions()
        
        # Analyze each requirement
        req_analysis = {}
        
        # Handle both old and new gap_analysis formats
        pillars = self.gap_data.get('pillars', [])
        
        # If no 'pillars' key, try the direct pillar structure
        if not pillars:
            for pillar_name, pillar_data in self.gap_data.items():
                if not isinstance(pillar_data, dict):
                    continue
                
                analysis = pillar_data.get('analysis', {})
                for req_name, req_data in analysis.items():
                    for sub_req_name, sub_req_data in req_data.items():
                        req_id = sub_req_name.split(':')[0].strip()
                        
                        # Get contributing papers
                        contributing_papers = sub_req_data.get('contributing_papers', [])
                        papers = [p.get('filename', '') for p in contributing_papers if isinstance(p, dict)]
                        
                        if not papers:
                            continue
                        
                        # Calculate diversity metrics
                        source_diversity = self._calculate_source_diversity(papers, author_groups, institution_groups)
                        convergence = self._calculate_convergence(papers)
                        
                        req_analysis[req_id] = {
                            'requirement': sub_req_name,
                            'total_papers': len(papers),
                            'unique_institutions': source_diversity['unique_institutions'],
                            'unique_author_groups': source_diversity['unique_author_groups'],
                            'diversity_score': source_diversity['diversity_score'],
                            'convergence_score': convergence['convergence_score'],
                            'needs_validation': source_diversity['diversity_score'] < 0.5,
                            'echo_chamber_risk': convergence['echo_chamber_risk']
                        }
        else:
            # Original format with 'pillars' list
            for pillar in pillars:
                for req in pillar['requirements']:
                    req_id = req['id']
                    
                    # Get contributing papers
                    papers = self._get_contributing_papers(req_id, pillar['name'])
                    
                    if not papers:
                        continue
                    
                    # Calculate diversity metrics
                    source_diversity = self._calculate_source_diversity(papers, author_groups, institution_groups)
                    convergence = self._calculate_convergence(papers)
                    
                    req_analysis[req_id] = {
                        'requirement': req['requirement'],
                        'total_papers': len(papers),
                        'unique_institutions': source_diversity['unique_institutions'],
                        'unique_author_groups': source_diversity['unique_author_groups'],
                        'diversity_score': source_diversity['diversity_score'],
                        'convergence_score': convergence['convergence_score'],
                        'needs_validation': source_diversity['diversity_score'] < 0.5,
                        'echo_chamber_risk': convergence['echo_chamber_risk']
                    }
        
        return {
            'requirement_analysis': req_analysis,
            'author_groups': author_groups,
            'institution_groups': institution_groups,
            'summary': self._generate_summary(req_analysis)
        }
    
    def _group_by_authors(self) -> Dict[str, List[str]]:
        """Group papers by lead author."""
        groups = defaultdict(list)
        
        for paper_file, review in self.reviews.items():
            metadata = review.get('metadata', {})
            lead_author = metadata.get('authors', ['Unknown'])[0] if metadata.get('authors') else 'Unknown'
            groups[lead_author].append(paper_file)
        
        return dict(groups)
    
    def _group_by_institutions(self) -> Dict[str, List[str]]:
        """Group papers by institution (extracted from metadata)."""
        groups = defaultdict(list)
        
        for paper_file, review in self.reviews.items():
            metadata = review.get('metadata', {})
            # Extract institution from affiliation if available
            affiliation = metadata.get('affiliation', 'Unknown')
            groups[affiliation].append(paper_file)
        
        return dict(groups)
    
    def _get_contributing_papers(self, req_id: str, pillar: str) -> List[str]:
        """Get papers contributing to a requirement."""
        papers = []
        
        for paper_file, review in self.reviews.items():
            judge = review.get('judge_analysis', {})
            
            for pillar_contrib in judge.get('pillar_contributions', []):
                if pillar_contrib.get('pillar_name') == pillar:
                    for sub_req in pillar_contrib.get('sub_requirements_addressed', []):
                        if sub_req.get('requirement_id') == req_id:
                            papers.append(paper_file)
        
        return papers
    
    def _calculate_source_diversity(self, papers: List[str], author_groups: Dict, 
                                   institution_groups: Dict) -> Dict:
        """Calculate source diversity score."""
        # Count unique authors and institutions
        unique_authors = set()
        unique_institutions = set()
        
        for paper in papers:
            for author, author_papers in author_groups.items():
                if paper in author_papers:
                    unique_authors.add(author)
            
            for institution, inst_papers in institution_groups.items():
                if paper in inst_papers:
                    unique_institutions.add(institution)
        
        # Diversity score: ratio of unique sources to total papers
        diversity_score = min(1.0, len(unique_institutions) / max(len(papers), 1))
        
        return {
            'unique_authors': len(unique_authors),
            'unique_author_groups': len(unique_authors),
            'unique_institutions': len(unique_institutions),
            'diversity_score': round(diversity_score, 2)
        }
    
    def _calculate_convergence(self, papers: List[str]) -> Dict:
        """Calculate evidence convergence."""
        # Check if papers cite each other (echo chamber)
        # Simplified: check if all papers from same institution
        
        institutions = set()
        for paper in papers:
            for review in self.reviews.values():
                if review.get('metadata', {}).get('affiliation'):
                    institutions.add(review['metadata']['affiliation'])
        
        echo_chamber_risk = len(institutions) <= 1 and len(papers) > 1
        
        convergence_score = 1.0 if len(institutions) >= 3 else 0.5
        
        return {
            'convergence_score': convergence_score,
            'echo_chamber_risk': echo_chamber_risk
        }
    
    def _generate_summary(self, req_analysis: Dict) -> Dict:
        """Generate summary statistics."""
        needs_validation = sum(1 for r in req_analysis.values() if r['needs_validation'])
        echo_chambers = sum(1 for r in req_analysis.values() if r['echo_chamber_risk'])
        
        return {
            'total_requirements_analyzed': len(req_analysis),
            'needs_independent_validation': needs_validation,
            'echo_chamber_risks': echo_chambers,
            'avg_diversity_score': round(
                sum(r['diversity_score'] for r in req_analysis.values()) / len(req_analysis), 2
            ) if req_analysis else 0.0
        }


def generate_triangulation_report(review_log: str, gap_analysis: str,
                                 output_file: str = 'gap_analysis_output/triangulation.json'):
    """Generate triangulation analysis report."""
    import os
    
    analyzer = TriangulationAnalyzer(review_log, gap_analysis)
    report = analyzer.analyze_triangulation()
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Triangulation report saved to {output_file}")
    
    print("\n" + "="*60)
    print("EVIDENCE TRIANGULATION ANALYSIS")
    print("="*60)
    
    summary = report['summary']
    print(f"\nSummary:")
    print(f"  Requirements Analyzed: {summary['total_requirements_analyzed']}")
    print(f"  Need Validation: {summary['needs_independent_validation']}")
    print(f"  Echo Chamber Risks: {summary['echo_chamber_risks']}")
    print(f"  Avg Diversity Score: {summary['avg_diversity_score']}")
    print("\n" + "="*60)
    
    return report
