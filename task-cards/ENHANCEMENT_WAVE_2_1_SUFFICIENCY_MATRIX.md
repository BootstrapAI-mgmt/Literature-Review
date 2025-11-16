# Task Card: Evidence Sufficiency Matrix

**Task ID:** ENHANCE-W2-1  
**Wave:** 2 (Deep Analysis)  
**Priority:** MEDIUM  
**Estimated Effort:** 10 hours  
**Status:** Not Started  
**Dependencies:** ENHANCE-W1-2 (Proof Scorecard)

---

## Objective

Analyze quality vs. quantity tradeoffs in evidence collection to identify critical gaps.

## Background

From Enhanced Analysis Proposal: "Many requirements are 'coverage complete' but lack depth." Need to distinguish between superficial coverage (many weak papers) and substantive proof (few strong papers).

## Success Criteria

- [ ] Matrix showing quality/quantity quadrants for each requirement
- [ ] Identify "hollow coverage" (high quantity, low quality)
- [ ] Identify "strong foundation" (high quantity, high quality)
- [ ] Identify "promising seeds" (low quantity, high quality - needs expansion)
- [ ] Actionable recommendations per quadrant

## Deliverables

### 1. Sufficiency Matrix Analyzer

**File:** `literature_review/analysis/sufficiency_matrix.py`

```python
"""
Evidence Sufficiency Matrix
Analyze quality vs. quantity tradeoffs in evidence collection.
"""

import json
from typing import Dict, List, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SufficiencyMatrixAnalyzer:
    """Analyze evidence sufficiency across quality/quantity dimensions."""
    
    # Thresholds for categorization
    QUANTITY_THRESHOLDS = {
        'low': 3,      # <3 papers
        'medium': 8,   # 3-8 papers
        'high': 8      # >8 papers
    }
    
    QUALITY_THRESHOLDS = {
        'low': 0.4,    # <40% avg alignment
        'medium': 0.7,  # 40-70% avg alignment
        'high': 0.7    # >70% avg alignment
    }
    
    def __init__(self, gap_analysis_file: str, review_log_file: str):
        """
        Initialize analyzer.
        
        Args:
            gap_analysis_file: Path to gap_analysis_report.json
            review_log_file: Path to review_log.json
        """
        self.gap_analysis_file = gap_analysis_file
        self.review_log_file = review_log_file
        
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
        
        with open(review_log_file, 'r') as f:
            self.review_log = json.load(f)
    
    def analyze_sufficiency(self) -> Dict:
        """
        Perform complete sufficiency analysis.
        
        Returns:
            Sufficiency matrix report
        """
        logger.info("Analyzing evidence sufficiency...")
        
        # Analyze each requirement
        requirement_analysis = {}
        
        for pillar in self.gap_data['pillars']:
            pillar_name = pillar['name']
            
            for req in pillar['requirements']:
                req_id = req['id']
                req_text = req['requirement']
                
                # Get contributing papers
                papers = self._get_contributing_papers(req_id, pillar_name, req_text)
                
                if not papers:
                    continue
                
                # Calculate metrics
                quantity = len(papers)
                quality = self._calculate_avg_alignment(papers, req_id, pillar_name)
                
                # Categorize
                quantity_level = self._categorize_quantity(quantity)
                quality_level = self._categorize_quality(quality)
                quadrant = self._assign_quadrant(quantity_level, quality_level)
                
                # Store analysis
                requirement_analysis[req_id] = {
                    'requirement': req_text,
                    'pillar': pillar_name,
                    'quantity': quantity,
                    'quality': quality,
                    'quantity_level': quantity_level,
                    'quality_level': quality_level,
                    'quadrant': quadrant,
                    'papers': [
                        {
                            'title': p['title'],
                            'alignment': p['alignment']
                        }
                        for p in papers
                    ]
                }
        
        # Group by quadrant
        quadrant_groups = self._group_by_quadrant(requirement_analysis)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(quadrant_groups)
        
        return {
            'summary': {
                'total_requirements_analyzed': len(requirement_analysis),
                'quadrant_distribution': {
                    quadrant: len(reqs)
                    for quadrant, reqs in quadrant_groups.items()
                }
            },
            'requirement_analysis': requirement_analysis,
            'quadrant_groups': quadrant_groups,
            'recommendations': recommendations,
            'matrix_visualization': self._create_matrix_data(requirement_analysis)
        }
    
    def _get_contributing_papers(self, req_id: str, pillar_name: str, req_text: str) -> List[Dict]:
        """Get papers contributing to a requirement."""
        papers = []
        
        for paper_file, review in self.review_log.items():
            if 'judge_analysis' not in review:
                continue
            
            judge = review['judge_analysis']
            
            # Check pillar contributions
            for pillar_contrib in judge.get('pillar_contributions', []):
                if pillar_contrib.get('pillar_name') != pillar_name:
                    continue
                
                # Check sub-requirements
                for sub_req in pillar_contrib.get('sub_requirements_addressed', []):
                    # Match by ID or text similarity
                    if sub_req.get('requirement_id') == req_id or \
                       self._fuzzy_match(sub_req.get('requirement', ''), req_text):
                        
                        papers.append({
                            'title': review.get('metadata', {}).get('title', paper_file),
                            'file': paper_file,
                            'alignment': sub_req.get('alignment_score', 0.0),
                            'contribution': sub_req.get('contribution_summary', '')
                        })
        
        return papers
    
    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy text matching."""
        # Normalize
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Exact match
        if t1 == t2:
            return True
        
        # Substring match
        if t1 in t2 or t2 in t1:
            return True
        
        # Simple word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        
        return (overlap / total) > threshold
    
    def _calculate_avg_alignment(self, papers: List[Dict], req_id: str, pillar: str) -> float:
        """Calculate average alignment score."""
        if not papers:
            return 0.0
        
        alignments = [p['alignment'] for p in papers if p['alignment'] > 0]
        
        if not alignments:
            return 0.0
        
        return sum(alignments) / len(alignments)
    
    def _categorize_quantity(self, quantity: int) -> str:
        """Categorize quantity level."""
        if quantity < self.QUANTITY_THRESHOLDS['low']:
            return 'low'
        elif quantity <= self.QUANTITY_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'high'
    
    def _categorize_quality(self, quality: float) -> str:
        """Categorize quality level."""
        if quality < self.QUALITY_THRESHOLDS['low']:
            return 'low'
        elif quality <= self.QUALITY_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'high'
    
    def _assign_quadrant(self, quantity_level: str, quality_level: str) -> str:
        """
        Assign quadrant based on quality/quantity levels.
        
        Quadrants:
        - Q1 (High Quantity, High Quality): Strong Foundation
        - Q2 (Low Quantity, High Quality): Promising Seeds
        - Q3 (Low Quantity, Low Quality): Critical Gap
        - Q4 (High Quantity, Low Quality): Hollow Coverage
        """
        if quantity_level == 'high' and quality_level == 'high':
            return 'Q1_Strong_Foundation'
        elif quantity_level in ['low', 'medium'] and quality_level == 'high':
            return 'Q2_Promising_Seeds'
        elif quantity_level in ['low', 'medium'] and quality_level in ['low', 'medium']:
            return 'Q3_Critical_Gap'
        else:  # high quantity, low/medium quality
            return 'Q4_Hollow_Coverage'
    
    def _group_by_quadrant(self, requirement_analysis: Dict) -> Dict[str, List[str]]:
        """Group requirements by quadrant."""
        quadrants = defaultdict(list)
        
        for req_id, analysis in requirement_analysis.items():
            quadrant = analysis['quadrant']
            quadrants[quadrant].append(req_id)
        
        return dict(quadrants)
    
    def _generate_recommendations(self, quadrant_groups: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Generate actionable recommendations per quadrant."""
        recommendations = {}
        
        # Q1: Strong Foundation
        q1_count = len(quadrant_groups.get('Q1_Strong_Foundation', []))
        if q1_count > 0:
            recommendations['Q1_Strong_Foundation'] = [
                f"✅ {q1_count} requirements have strong evidence foundation",
                "✅ These are publication-ready - consider consolidating into review papers",
                "💡 Use these as benchmarks for evidence quality in other requirements"
            ]
        
        # Q2: Promising Seeds
        q2_count = len(quadrant_groups.get('Q2_Promising_Seeds', []))
        if q2_count > 0:
            recommendations['Q2_Promising_Seeds'] = [
                f"⚠️ {q2_count} requirements have high-quality but limited evidence",
                "🎯 Priority action: Run targeted searches to find more papers in these areas",
                "💡 These could become Q1 with 3-5 more high-quality papers",
                "💡 Consider Deep Reviewer to extract maximum value from existing papers"
            ]
        
        # Q3: Critical Gap
        q3_count = len(quadrant_groups.get('Q3_Critical_Gap', []))
        if q3_count > 0:
            recommendations['Q3_Critical_Gap'] = [
                f"🚨 {q3_count} requirements have critical evidence gaps",
                "🎯 Urgent action: Expand searches or relax inclusion criteria",
                "💡 Consider whether requirements are too specific or poorly defined",
                "💡 May need expert consultation or primary research"
            ]
        
        # Q4: Hollow Coverage
        q4_count = len(quadrant_groups.get('Q4_Hollow_Coverage', []))
        if q4_count > 0:
            recommendations['Q4_Hollow_Coverage'] = [
                f"⚠️ {q4_count} requirements have many papers but low alignment",
                "🎯 Action: Review and refine requirement definitions",
                "🎯 Action: Apply stricter inclusion criteria to filter weak papers",
                "💡 Quality > Quantity - consider removing weakly aligned papers",
                "💡 May indicate search queries are too broad"
            ]
        
        return recommendations
    
    def _create_matrix_data(self, requirement_analysis: Dict) -> Dict:
        """Create data for matrix visualization."""
        matrix_data = {
            'requirements': [],
            'quadrants': {
                'Q1_Strong_Foundation': {'min_quantity': 8, 'min_quality': 0.7, 'color': '#28a745'},
                'Q2_Promising_Seeds': {'max_quantity': 8, 'min_quality': 0.7, 'color': '#ffc107'},
                'Q3_Critical_Gap': {'max_quantity': 8, 'max_quality': 0.7, 'color': '#dc3545'},
                'Q4_Hollow_Coverage': {'min_quantity': 8, 'max_quality': 0.7, 'color': '#fd7e14'}
            }
        }
        
        for req_id, analysis in requirement_analysis.items():
            matrix_data['requirements'].append({
                'id': req_id,
                'requirement': analysis['requirement'][:50] + '...',
                'pillar': analysis['pillar'],
                'x': analysis['quantity'],
                'y': analysis['quality'],
                'quadrant': analysis['quadrant'],
                'papers': analysis['papers']
            })
        
        return matrix_data


def generate_sufficiency_report(gap_analysis_file: str, review_log_file: str,
                               output_file: str = 'gap_analysis_output/sufficiency_matrix.json'):
    """
    Generate evidence sufficiency matrix report.
    
    Args:
        gap_analysis_file: Path to gap analysis report
        review_log_file: Path to review log
        output_file: Output file path
    """
    import os
    
    analyzer = SufficiencyMatrixAnalyzer(gap_analysis_file, review_log_file)
    report = analyzer.analyze_sufficiency()
    
    # Save report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Sufficiency matrix report saved to {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("EVIDENCE SUFFICIENCY MATRIX")
    print("="*60)
    
    summary = report['summary']
    print(f"\nAnalyzed {summary['total_requirements_analyzed']} requirements\n")
    
    print("Quadrant Distribution:")
    for quadrant, count in summary['quadrant_distribution'].items():
        print(f"  {quadrant}: {count}")
    
    print("\nRecommendations:")
    for quadrant, recs in report['recommendations'].items():
        print(f"\n{quadrant}:")
        for rec in recs:
            print(f"  {rec}")
    
    print("\n" + "="*60)
    
    return report
```

### 2. HTML Visualization

**File:** `literature_review/visualization/sufficiency_matrix_viz.py`

```python
"""
Sufficiency Matrix Visualization
Interactive scatter plot showing quality vs. quantity.
"""

import json


def generate_sufficiency_matrix_html(report_file: str, output_file: str):
    """Generate interactive HTML visualization of sufficiency matrix."""
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    matrix_data = report['matrix_visualization']
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Evidence Sufficiency Matrix</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .legend {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .legend-item {{
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid;
        }}
        .q1 {{ border-color: #28a745; background: #d4edda; }}
        .q2 {{ border-color: #ffc107; background: #fff3cd; }}
        .q3 {{ border-color: #dc3545; background: #f8d7da; }}
        .q4 {{ border-color: #fd7e14; background: #ffe5d0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Evidence Sufficiency Matrix</h1>
        <p>Quality vs. Quantity analysis of evidence for each requirement</p>
        
        <div class="legend">
            <div class="legend-item q1">
                <strong>Q1: Strong Foundation</strong><br>
                High quantity (8+ papers), High quality (70%+ alignment)<br>
                ✅ Publication-ready
            </div>
            <div class="legend-item q2">
                <strong>Q2: Promising Seeds</strong><br>
                Low quantity (&lt;8 papers), High quality (70%+ alignment)<br>
                🎯 Needs more papers
            </div>
            <div class="legend-item q3">
                <strong>Q3: Critical Gap</strong><br>
                Low quantity (&lt;8 papers), Low quality (&lt;70% alignment)<br>
                🚨 Urgent attention needed
            </div>
            <div class="legend-item q4">
                <strong>Q4: Hollow Coverage</strong><br>
                High quantity (8+ papers), Low quality (&lt;70% alignment)<br>
                ⚠️ Refine requirements
            </div>
        </div>
        
        <div id="matrix-plot"></div>
    </div>
    
    <script>
        const requirements = {json.dumps(matrix_data['requirements'])};
        const quadrants = {json.dumps(matrix_data['quadrants'])};
        
        // Group by quadrant
        const byQuadrant = {{}};
        requirements.forEach(req => {{
            if (!byQuadrant[req.quadrant]) {{
                byQuadrant[req.quadrant] = [];
            }}
            byQuadrant[req.quadrant].push(req);
        }});
        
        // Create traces
        const traces = Object.keys(quadrants).map(quadrant => {{
            const reqs = byQuadrant[quadrant] || [];
            const config = quadrants[quadrant];
            
            return {{
                x: reqs.map(r => r.x),
                y: reqs.map(r => r.y),
                mode: 'markers',
                type: 'scatter',
                name: quadrant.replace(/_/g, ' '),
                marker: {{
                    size: 12,
                    color: config.color,
                    line: {{
                        color: 'white',
                        width: 2
                    }}
                }},
                text: reqs.map(r => 
                    `<b>${{r.pillar}}</b><br>${{r.requirement}}<br>` +
                    `Papers: ${{r.x}}, Avg Quality: ${{(r.y * 100).toFixed(1)}}%<br>` +
                    `<br><b>Top Papers:</b><br>` +
                    r.papers.slice(0, 3).map(p => 
                        `- ${{p.title.substring(0, 50)}}... (${{(p.alignment * 100).toFixed(0)}}%)`
                    ).join('<br>')
                ),
                hovertemplate: '%{{text}}<extra></extra>'
            }};
        }});
        
        const layout = {{
            title: 'Evidence Sufficiency Matrix',
            xaxis: {{
                title: 'Number of Papers (Quantity)',
                gridcolor: '#e0e0e0',
                zeroline: false
            }},
            yaxis: {{
                title: 'Average Alignment Score (Quality)',
                tickformat: '.0%',
                gridcolor: '#e0e0e0',
                zeroline: false
            }},
            hovermode: 'closest',
            plot_bgcolor: '#fafafa',
            height: 600,
            shapes: [
                // Quadrant dividers
                {{
                    type: 'line',
                    x0: 8, x1: 8, y0: 0, y1: 1,
                    line: {{ dash: 'dash', color: '#999', width: 2 }}
                }},
                {{
                    type: 'line',
                    x0: 0, x1: 50, y0: 0.7, y1: 0.7,
                    line: {{ dash: 'dash', color: '#999', width: 2 }}
                }}
            ]
        }};
        
        Plotly.newPlot('matrix-plot', traces, layout);
    </script>
</body>
</html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Sufficiency matrix visualization saved to {output_file}")
```

### 3. Integration with Gap Analysis

**File:** `DeepRequirementsAnalyzer.py` (additions)

```python
from literature_review.analysis.sufficiency_matrix import generate_sufficiency_report
from literature_review.visualization.sufficiency_matrix_viz import generate_sufficiency_matrix_html

class DeepRequirementsAnalyzer:
    def generate_outputs(self):
        """Generate all analysis outputs."""
        
        # ... existing outputs ...
        
        # NEW: Generate sufficiency matrix
        logger.info("Generating evidence sufficiency matrix...")
        generate_sufficiency_report(
            gap_analysis_file='gap_analysis_output/gap_analysis_report.json',
            review_log_file='review_log.json',
            output_file='gap_analysis_output/sufficiency_matrix.json'
        )
        
        # Generate HTML visualization
        generate_sufficiency_matrix_html(
            report_file='gap_analysis_output/sufficiency_matrix.json',
            output_file='gap_analysis_output/sufficiency_matrix.html'
        )
```

## Testing Plan

### Unit Tests

```python
# tests/unit/test_sufficiency_matrix.py

def test_quadrant_assignment():
    """Test quadrant assignment logic."""
    analyzer = SufficiencyMatrixAnalyzer('test_gap.json', 'test_review.json')
    
    assert analyzer._assign_quadrant('high', 'high') == 'Q1_Strong_Foundation'
    assert analyzer._assign_quadrant('low', 'high') == 'Q2_Promising_Seeds'
    assert analyzer._assign_quadrant('low', 'low') == 'Q3_Critical_Gap'
    assert analyzer._assign_quadrant('high', 'low') == 'Q4_Hollow_Coverage'
```

### Integration Tests

```bash
# Run with real data
python -c "from literature_review.analysis.sufficiency_matrix import generate_sufficiency_report; generate_sufficiency_report('gap_analysis_output/gap_analysis_report.json', 'review_log.json')"

# Open visualization
open gap_analysis_output/sufficiency_matrix.html
```

## Acceptance Criteria

- [ ] Matrix correctly categorizes requirements into 4 quadrants
- [ ] Recommendations are actionable and specific
- [ ] HTML visualization is interactive and informative
- [ ] Identifies hollow coverage (many weak papers)
- [ ] Identifies promising seeds (few strong papers)
- [ ] Integrated with gap analysis pipeline

## Integration Points

- Uses output from `gap_analysis_report.json`
- Uses output from `review_log.json`
- Integrated with `DeepRequirementsAnalyzer.py`
- Complements Proof Scorecard (ENHANCE-W1-2)

## Notes

- Thresholds (8 papers, 70% quality) are configurable
- Consider pillar-specific thresholds if evidence density varies
- Quadrant assignment helps prioritize search efforts

## Related Tasks

- ENHANCE-W1-2 (Proof Scorecard) - Provides publication-readiness context
- ENHANCE-W3-2 (Search Optimizer) - Uses sufficiency gaps to guide searches

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 2 (Week 3-4)
