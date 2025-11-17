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
        
        req_text = analysis['requirement'][:80] + "..." if len(analysis['requirement']) > 80 else analysis['requirement']
        html += f"""
                <tr>
                    <td><strong>{req_id}</strong><br><small>{req_text}</small></td>
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
