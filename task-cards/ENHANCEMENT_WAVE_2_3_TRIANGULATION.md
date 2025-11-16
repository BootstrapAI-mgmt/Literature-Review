# Task Card: Evidence Triangulation Analysis

**Task ID:** ENHANCE-W2-3  
**Wave:** 2 (Deep Analysis)  
**Priority:** MEDIUM  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** None

---

## Objective

Detect bias, identify source diversity gaps, and validate evidence convergence across multiple independent sources.

## Background

From Enhanced Analysis Proposal: "Multiple independent sources converging on same finding = stronger evidence. Single-source findings need validation."

## Success Criteria

- [ ] Group papers by research groups/institutions
- [ ] Detect single-source dependencies
- [ ] Calculate source diversity scores
- [ ] Identify echo chambers (citations between same group)
- [ ] Flag requirements needing independent validation

## Deliverables

### 1. Triangulation Analyzer

**File:** `literature_review/analysis/triangulation.py`

```python
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
            self.reviews = json.load(f)
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
        
        for pillar in self.gap_data['pillars']:
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
```

### 2. HTML Visualization

**File:** `literature_review/visualization/triangulation_viz.py`

```python
"""
Triangulation Analysis Visualization
Generate interactive reports showing source diversity and bias risks.
"""

import json
import os


def generate_triangulation_html(report_file: str, output_file: str):
    """Generate HTML visualization for triangulation analysis."""
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    req_analysis = report['requirement_analysis']
    summary = report['summary']
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Evidence Triangulation Analysis</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #2575fc;
            padding-bottom: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
        }}
        .summary-card h2 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .summary-card p {{
            margin: 10px 0 0 0;
            opacity: 0.95;
        }}
        .risk-section {{
            margin: 30px 0;
            padding: 20px;
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            border-radius: 5px;
        }}
        .risk-section h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .validation-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8d7da;
            border-left: 5px solid #dc3545;
            border-radius: 5px;
        }}
        .validation-section h3 {{
            margin-top: 0;
            color: #721c24;
        }}
        .requirement-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .requirement-table th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        .requirement-table td {{
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .requirement-table tr:hover {{
            background: #f8f9fa;
        }}
        .diversity-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85em;
        }}
        .diversity-high {{ background: #d4edda; color: #155724; }}
        .diversity-medium {{ background: #fff3cd; color: #856404; }}
        .diversity-low {{ background: #f8d7da; color: #721c24; }}
        .echo-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            background: #dc3545;
            color: white;
            font-weight: 600;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Evidence Triangulation Analysis</h1>
        <p>Source diversity and bias detection across requirements</p>
        
        <div class="summary-grid">
            <div class="summary-card">
                <h2>{summary['total_requirements_analyzed']}</h2>
                <p>Requirements Analyzed</p>
            </div>
            <div class="summary-card">
                <h2>{summary['needs_independent_validation']}</h2>
                <p>Need Independent Validation</p>
            </div>
            <div class="summary-card">
                <h2>{summary['echo_chamber_risks']}</h2>
                <p>Echo Chamber Risks</p>
            </div>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                <h2>{summary['avg_diversity_score']}</h2>
                <p>Avg Diversity Score</p>
            </div>
        </div>"""
    
    # Add risk section if there are echo chamber risks
    if summary['echo_chamber_risks'] > 0:
        html += f"""
        <div class="risk-section">
            <h3>⚠️ Echo Chamber Risks Detected</h3>
            <p>{summary['echo_chamber_risks']} requirements show evidence of echo chamber bias (papers from same institution/research group citing each other).</p>
            <p><strong>Recommendation:</strong> Seek independent validation from diverse research groups.</p>
        </div>"""
    
    # Add validation section if requirements need independent validation
    if summary['needs_independent_validation'] > 0:
        html += f"""
        <div class="validation-section">
            <h3>🚨 Independent Validation Needed</h3>
            <p>{summary['needs_independent_validation']} requirements have low source diversity (&lt;50%) and need independent validation.</p>
            <p><strong>Action Required:</strong> Search for papers from different institutions and research groups.</p>
        </div>"""
    
    html += """
        <h2>Requirement Diversity Analysis</h2>
        <table class="requirement-table">
            <thead>
                <tr>
                    <th>Requirement</th>
                    <th>Papers</th>
                    <th>Institutions</th>
                    <th>Diversity Score</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>"""
    
    # Sort by diversity score (lowest first - these need attention)
    sorted_reqs = sorted(
        req_analysis.items(),
        key=lambda x: x[1]['diversity_score']
    )
    
    for req_id, analysis in sorted_reqs:
        diversity_class = 'diversity-high' if analysis['diversity_score'] >= 0.7 else \
                         'diversity-medium' if analysis['diversity_score'] >= 0.5 else \
                         'diversity-low'
        
        status_badges = []
        if analysis['needs_validation']:
            status_badges.append('<span class="diversity-badge diversity-low">Needs Validation</span>')
        if analysis['echo_chamber_risk']:
            status_badges.append('<span class="echo-badge">Echo Chamber Risk</span>')
        if not status_badges:
            status_badges.append('<span class="diversity-badge diversity-high">✓ Validated</span>')
        
        html += f"""
                <tr>
                    <td><strong>{req_id}</strong><br><small>{analysis['requirement'][:80]}...</small></td>
                    <td>{analysis['total_papers']}</td>
                    <td>{analysis['unique_institutions']}</td>
                    <td><span class="diversity-badge {diversity_class}">{analysis['diversity_score']:.0%}</span></td>
                    <td>{' '.join(status_badges)}</td>
                </tr>"""
    
    html += """
            </tbody>
        </table>
        
        <div id="diversity-chart"></div>
    </div>
    
    <script>
        // Diversity distribution chart
        const requirements = """ + json.dumps([
            {
                'req_id': req_id,
                'diversity': analysis['diversity_score'],
                'papers': analysis['total_papers'],
                'institutions': analysis['unique_institutions']
            }
            for req_id, analysis in sorted_reqs
        ]) + """;
        
        const trace = {
            x: requirements.map(r => r.req_id),
            y: requirements.map(r => r.diversity),
            type: 'bar',
            marker: {
                color: requirements.map(r => 
                    r.diversity >= 0.7 ? '#28a745' :
                    r.diversity >= 0.5 ? '#ffc107' :
                    '#dc3545'
                )
            },
            text: requirements.map(r => 
                `${r.institutions} institutions<br>${r.papers} papers`
            ),
            hovertemplate: '%{x}<br>Diversity: %{y:.0%}<br>%{text}<extra></extra>'
        };
        
        const layout = {
            title: 'Source Diversity by Requirement',
            xaxis: {
                title: 'Requirement ID',
                tickangle: -45
            },
            yaxis: {
                title: 'Diversity Score',
                tickformat: '.0%',
                range: [0, 1]
            },
            shapes: [
                {
                    type: 'line',
                    x0: -0.5,
                    x1: requirements.length,
                    y0: 0.5,
                    y1: 0.5,
                    line: {
                        color: '#dc3545',
                        width: 2,
                        dash: 'dash'
                    }
                }
            ],
            annotations: [
                {
                    x: requirements.length - 1,
                    y: 0.52,
                    text: 'Validation Threshold (50%)',
                    showarrow: false,
                    font: { color: '#dc3545' }
                }
            ],
            height: 500
        };
        
        Plotly.newPlot('diversity-chart', [trace], layout);
    </script>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Triangulation visualization saved to {output_file}")
```

### 3. Integration

**File:** `DeepRequirementsAnalyzer.py` (additions)

```python
from literature_review.analysis.triangulation import generate_triangulation_report
from literature_review.visualization.triangulation_viz import generate_triangulation_html

class DeepRequirementsAnalyzer:
    def generate_outputs(self):
        """Generate all analysis outputs."""
        
        # ... existing outputs ...
        
        # NEW: Generate triangulation analysis
        logger.info("Analyzing evidence triangulation...")
        generate_triangulation_report(
            review_log='review_log.json',
            gap_analysis='gap_analysis_output/gap_analysis_report.json',
            output_file='gap_analysis_output/triangulation.json'
        )
        
        # Generate HTML visualization
        generate_triangulation_html(
            report_file='gap_analysis_output/triangulation.json',
            output_file='gap_analysis_output/triangulation.html'
        )
        
        logger.info("Triangulation analysis complete")
```

### 4. Enhanced Metadata Requirements

For triangulation to work effectively, papers need author and institution metadata.

**Required metadata in paper JSON:**

```json
{
  "metadata": {
    "title": "Paper Title",
    "authors": ["Dr. Jane Smith", "Dr. John Doe"],
    "affiliation": "MIT",
    "institution": "Massachusetts Institute of Technology",
    "publication_year": 2024
  }
}
```

### 5. CLI Tool

**File:** `scripts/analyze_triangulation.py`

```python
#!/usr/bin/env python3
"""Analyze evidence triangulation and source diversity."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.analysis.triangulation import generate_triangulation_report
from literature_review.visualization.triangulation_viz import generate_triangulation_html
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Analyze evidence triangulation and detect bias'
    )
    parser.add_argument(
        '--review-log',
        default='review_log.json',
        help='Path to review log'
    )
    parser.add_argument(
        '--gap-analysis',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis report'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/triangulation.json',
        help='Output file for analysis'
    )
    parser.add_argument(
        '--viz',
        default='gap_analysis_output/triangulation.html',
        help='Output file for visualization'
    )
    parser.add_argument(
        '--open',
        action='store_true',
        help='Open visualization in browser'
    )
    
    args = parser.parse_args()
    
    # Generate report
    print("Analyzing evidence triangulation...")
    report = generate_triangulation_report(
        review_log=args.review_log,
        gap_analysis=args.gap_analysis,
        output_file=args.output
    )
    
    # Generate visualization
    print("\nGenerating visualization...")
    generate_triangulation_html(
        report_file=args.output,
        output_file=args.viz
    )
    
    print(f"\n✅ Analysis complete!")
    print(f"   Report: {args.output}")
    print(f"   Visualization: {args.viz}")
    
    # Open if requested
    if args.open:
        import webbrowser
        webbrowser.open(f'file://{os.path.abspath(args.viz)}')
        print(f"\n🌐 Opened in browser")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_triangulation.py`

```python
"""Unit tests for evidence triangulation analysis."""

import pytest
import json
import tempfile
from literature_review.analysis.triangulation import TriangulationAnalyzer


@pytest.fixture
def sample_review_log():
    """Sample review log with author/institution data."""
    return {
        "paper1.json": {
            "metadata": {
                "title": "Paper 1",
                "authors": ["Author A"],
                "affiliation": "MIT"
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.8
                            }
                        ]
                    }
                ]
            }
        },
        "paper2.json": {
            "metadata": {
                "title": "Paper 2",
                "authors": ["Author B"],
                "affiliation": "Stanford"
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.7
                            }
                        ]
                    }
                ]
            }
        },
        "paper3.json": {
            "metadata": {
                "title": "Paper 3",
                "authors": ["Author A"],
                "affiliation": "MIT"
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.6
                            }
                        ]
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_gap_data():
    """Sample gap analysis data."""
    return {
        "pillars": [
            {
                "name": "Test Pillar",
                "requirements": [
                    {
                        "id": "P1-R1",
                        "requirement": "Test Req 1",
                        "papers_found": 3,
                        "gap_severity": "Low"
                    }
                ]
            }
        ]
    }


def test_author_grouping(tmp_path, sample_review_log, sample_gap_data):
    """Test grouping papers by author."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    author_groups = analyzer._group_by_authors()
    
    assert "Author A" in author_groups
    assert len(author_groups["Author A"]) == 2  # paper1 and paper3


def test_institution_grouping(tmp_path, sample_review_log, sample_gap_data):
    """Test grouping papers by institution."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    inst_groups = analyzer._group_by_institutions()
    
    assert "MIT" in inst_groups
    assert "Stanford" in inst_groups
    assert len(inst_groups["MIT"]) == 2


def test_source_diversity_calculation(tmp_path, sample_review_log, sample_gap_data):
    """Test source diversity score calculation."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    author_groups = analyzer._group_by_authors()
    inst_groups = analyzer._group_by_institutions()
    
    papers = ["paper1.json", "paper2.json", "paper3.json"]
    diversity = analyzer._calculate_source_diversity(papers, author_groups, inst_groups)
    
    # 3 papers from 2 institutions = 2/3 = 0.67 diversity
    assert diversity['unique_institutions'] == 2
    assert 0.6 <= diversity['diversity_score'] <= 0.7


def test_echo_chamber_detection(tmp_path, sample_review_log, sample_gap_data):
    """Test echo chamber risk detection."""
    # Modify to have all papers from same institution
    echo_review_log = sample_review_log.copy()
    for paper in echo_review_log.values():
        paper['metadata']['affiliation'] = "MIT"
    
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(echo_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()
    
    # Should detect echo chamber risk
    assert report['summary']['echo_chamber_risks'] > 0


def test_full_analysis(tmp_path, sample_review_log, sample_gap_data):
    """Test complete triangulation analysis."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()
    
    assert 'requirement_analysis' in report
    assert 'summary' in report
    assert report['summary']['total_requirements_analyzed'] == 1
```

### Integration Tests

```bash
# Test with real data
python scripts/analyze_triangulation.py --review-log review_log.json --gap-analysis gap_analysis_output/gap_analysis_report.json

# Verify outputs
ls -lh gap_analysis_output/triangulation.json
ls -lh gap_analysis_output/triangulation.html

# Check for echo chamber risks
cat gap_analysis_output/triangulation.json | jq '.summary.echo_chamber_risks'

# Check requirements needing validation
cat gap_analysis_output/triangulation.json | jq '.summary.needs_independent_validation'

# Open visualization
python scripts/analyze_triangulation.py --open
```

### Manual Testing Checklist

- [ ] Correct grouping of papers by author
- [ ] Correct grouping of papers by institution
- [ ] Diversity scores calculated accurately
- [ ] Echo chamber risks flagged appropriately
- [ ] Requirements needing validation identified
- [ ] HTML visualization renders correctly
- [ ] Bar chart shows diversity distribution
- [ ] Warning sections appear when risks detected

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 2 (Week 3-4)
