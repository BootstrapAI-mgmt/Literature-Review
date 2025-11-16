"""Generate interactive HTML visualization for proof scorecard."""

import json
from typing import Dict


def generate_html(scorecard: Dict, output_file: str):
    """Generate interactive HTML dashboard."""
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proof Completeness Scorecard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .timestamp {{
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .overall-status {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 30px;
        }}
        .score {{
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .score.low {{ color: #dc3545; }}
        .score.medium {{ color: #ffc107; }}
        .score.high {{ color: #28a745; }}
        .verdict {{
            font-size: 20px;
            margin: 10px 0;
        }}
        .headline {{
            font-size: 16px;
            color: #666;
            margin: 10px 0;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .goal-card {{
            background: #fff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 20px;
            margin: 15px 0;
        }}
        .goal-header {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        .status-indicator {{
            font-size: 32px;
            margin-right: 15px;
        }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 4px;
            height: 24px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            background: #28a745;
            height: 100%;
            text-align: center;
            color: white;
            font-size: 12px;
            line-height: 24px;
            transition: width 0.3s ease;
        }}
        .progress-fill.low {{ background: #dc3545; }}
        .progress-fill.medium {{ background: #ffc107; }}
        .progress-fill.high {{ background: #28a745; }}
        .metric {{
            display: inline-block;
            margin: 5px 15px 5px 0;
            font-size: 14px;
        }}
        .metric-label {{
            color: #666;
            margin-right: 5px;
        }}
        .metric-value {{
            font-weight: bold;
        }}
        .checklist {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .checklist-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .checklist-number {{
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
        }}
        .checklist-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .next-steps {{
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin: 20px 0;
        }}
        .next-steps ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .next-steps li {{
            margin: 8px 0;
        }}
        .publication-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .pub-option {{
            border: 2px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}
        .pub-option.viable {{
            border-color: #28a745;
            background: #d4edda;
        }}
        .pub-option.maybe {{
            border-color: #ffc107;
            background: #fff3cd;
        }}
        .pub-option.not-viable {{
            border-color: #dc3545;
            background: #f8d7da;
        }}
        .blocker-list {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .blocker-list li {{
            margin: 5px 0;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Proof Completeness Scorecard</h1>
        <div class="timestamp">Generated: {scorecard['timestamp']}</div>
        
        <div class="overall-status">
            <div class="score {get_score_class(scorecard['overall_proof_status']['proof_readiness_score'])}">
                {scorecard['overall_proof_status']['proof_readiness_score']:.1f}%
            </div>
            <div class="verdict">
                Verdict: {format_verdict(scorecard['overall_proof_status']['verdict'])}
            </div>
            <div class="headline">
                {scorecard['overall_proof_status']['headline']}
            </div>
        </div>
        
        <div class="section">
            <h2>Research Goals</h2>
            {generate_goals_html(scorecard['research_goals'])}
        </div>
        
        <div class="section">
            <h2>Proof Requirements Checklist</h2>
            {generate_checklist_html(scorecard['proof_requirements_checklist'])}
        </div>
        
        <div class="section">
            <h2>Publication Viability</h2>
            {generate_publication_html(scorecard['publication_viability'])}
        </div>
        
        <div class="next-steps">
            <h3>🎯 Critical Next Steps</h3>
            <ol>
                {generate_next_steps_html(scorecard['critical_next_steps'])}
            </ol>
        </div>
        
        <div class="section">
            <h2>Pillar 7 Readiness (System Integration)</h2>
            {generate_pillar_7_html(scorecard['pillar_7_readiness'])}
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)


def get_score_class(score: float) -> str:
    """Get CSS class for score."""
    if score >= 60:
        return 'high'
    elif score >= 40:
        return 'medium'
    else:
        return 'low'


def format_verdict(verdict: str) -> str:
    """Format verdict for display."""
    return verdict.replace('_', ' ').title()


def get_status_emoji(status: str) -> str:
    """Get emoji for proof status."""
    status_map = {
        'PROVEN': '🟢',
        'PROBABLE': '🟡',
        'POSSIBLE': '🟡',
        'INSUFFICIENT': '🟠',
        'UNPROVEN': '🔴'
    }
    return status_map.get(status, '⚪')


def generate_goals_html(goals: list) -> str:
    """Generate HTML for research goals section."""
    html_parts = []
    
    for goal in goals:
        status_emoji = get_status_emoji(goal['proof_status'])
        completeness = goal['completeness']
        progress_class = get_score_class(completeness)
        
        blockers_html = ""
        if goal.get('blocking_factors'):
            blockers_html = "<ul class='blocker-list'>"
            for blocker in goal['blocking_factors'][:3]:  # Top 3
                blockers_html += f"<li>{blocker}</li>"
            blockers_html += "</ul>"
        
        dependency_html = ""
        if goal.get('dependency'):
            dependency_html = f"<div class='metric'><span class='metric-label'>Dependency:</span><span class='metric-value'>{goal['dependency']}</span></div>"
        
        html_parts.append(f"""
        <div class="goal-card">
            <div class="goal-header">
                <div class="status-indicator">{status_emoji}</div>
                <div>
                    <strong>{goal['goal']}</strong>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
                        {', '.join(goal['pillars'])}
                    </div>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill {progress_class}" style="width: {completeness}%">
                    {completeness:.1f}%
                </div>
            </div>
            <div>
                <div class="metric">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">{goal['proof_status']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sufficiency:</span>
                    <span class="metric-value">{goal['sufficiency']:.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Minimum Viable:</span>
                    <span class="metric-value">{goal['minimum_viable']}%</span>
                </div>
                {dependency_html}
            </div>
            <div style="margin-top: 10px;">
                <div class="metric">
                    <span class="metric-label">Deficit:</span>
                    <span class="metric-value">{goal['current_deficit']:.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Papers Needed:</span>
                    <span class="metric-value">{goal.get('estimated_papers_needed', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Timeline:</span>
                    <span class="metric-value">{goal.get('estimated_timeline_weeks', 0)} weeks</span>
                </div>
            </div>
            {blockers_html}
        </div>
        """)
    
    return '\n'.join(html_parts)


def generate_checklist_html(checklist: dict) -> str:
    """Generate HTML for proof requirements checklist."""
    return f"""
    <div class="checklist">
        <div class="checklist-item">
            <div class="checklist-number" style="color: #28a745;">{checklist['proven']}</div>
            <div class="checklist-label">Proven (≥80%)</div>
        </div>
        <div class="checklist-item">
            <div class="checklist-number" style="color: #17a2b8;">{checklist['probable']}</div>
            <div class="checklist-label">Probable (60-79%)</div>
        </div>
        <div class="checklist-item">
            <div class="checklist-number" style="color: #ffc107;">{checklist['possible']}</div>
            <div class="checklist-label">Possible (40-59%)</div>
        </div>
        <div class="checklist-item">
            <div class="checklist-number" style="color: #fd7e14;">{checklist['insufficient']}</div>
            <div class="checklist-label">Insufficient (20-39%)</div>
        </div>
        <div class="checklist-item">
            <div class="checklist-number" style="color: #dc3545;">{checklist['unproven']}</div>
            <div class="checklist-label">Unproven (<20%)</div>
        </div>
        <div class="checklist-item">
            <div class="checklist-number" style="color: #007bff;">{checklist['total_requirements']}</div>
            <div class="checklist-label">Total Requirements</div>
        </div>
    </div>
    <div style="text-align: center; margin-top: 20px; font-size: 18px;">
        <strong>{checklist['percent_proven']:.1f}%</strong> of requirements are proven
    </div>
    """


def generate_publication_html(pub_viability: dict) -> str:
    """Generate HTML for publication viability section."""
    tier1_class = 'viable' if pub_viability['tier_1_journal'] else 'not-viable'
    tier2_class = 'viable' if pub_viability['tier_2_journal'] else 'not-viable'
    conf_class = 'maybe' if pub_viability['conference_paper'] == 'MAYBE' else 'not-viable'
    
    return f"""
    <div class="publication-grid">
        <div class="pub-option {tier1_class}">
            <h4>Tier 1 Journal</h4>
            <p>Nature, Science, etc.</p>
            <strong>{'✅ VIABLE' if pub_viability['tier_1_journal'] else '❌ NOT VIABLE'}</strong>
        </div>
        <div class="pub-option {tier2_class}">
            <h4>Tier 2 Journal</h4>
            <p>Specialized journals</p>
            <strong>{'✅ VIABLE' if pub_viability['tier_2_journal'] else '❌ NOT VIABLE'}</strong>
        </div>
        <div class="pub-option {conf_class}">
            <h4>Conference Paper</h4>
            <p>Academic conferences</p>
            <strong>{pub_viability['conference_paper']}</strong>
        </div>
        <div class="pub-option viable">
            <h4>Preprint</h4>
            <p>arXiv, bioRxiv</p>
            <strong>✅ ALWAYS VIABLE</strong>
        </div>
    </div>
    <div style="background: #e7f3ff; padding: 15px; border-radius: 6px; margin-top: 20px;">
        <strong>Recommended Venue:</strong> {pub_viability['recommended_venue']}
    </div>
    """


def generate_next_steps_html(next_steps: list) -> str:
    """Generate HTML for next steps list."""
    return '\n'.join(f"<li>{step}</li>" for step in next_steps)


def generate_pillar_7_html(p7_readiness: dict) -> str:
    """Generate HTML for Pillar 7 readiness section."""
    ready = p7_readiness['ready_for_integration']
    status_class = 'viable' if ready else 'not-viable'
    
    blockers_html = ""
    if p7_readiness.get('blocking_pillars'):
        blockers_html = "<h4>Blocking Pillars:</h4><ul class='blocker-list'>"
        for blocker in p7_readiness['blocking_pillars']:
            blockers_html += f"""
            <li>
                <strong>{blocker['pillar']}</strong>: 
                {blocker['completeness']:.1f}% (needs {blocker['threshold']}%) - 
                {blocker['papers_needed']} papers needed
            </li>
            """
        blockers_html += "</ul>"
    
    return f"""
    <div class="pub-option {status_class}" style="max-width: 100%;">
        <p>{p7_readiness['description']}</p>
        <div class="progress-bar">
            <div class="progress-fill {get_score_class(p7_readiness['current_readiness'])}" 
                 style="width: {p7_readiness['current_readiness']}%">
                {p7_readiness['current_readiness']:.1f}%
            </div>
        </div>
        <div style="margin-top: 15px;">
            <div class="metric">
                <span class="metric-label">Target:</span>
                <span class="metric-value">{p7_readiness['target_readiness']}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Ready:</span>
                <span class="metric-value">{'✅ YES' if ready else '❌ NO'}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Earliest Possible:</span>
                <span class="metric-value">{p7_readiness['earliest_possible_date']}</span>
            </div>
        </div>
        {blockers_html}
    </div>
    """
