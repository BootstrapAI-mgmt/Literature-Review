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
                        `- ${{p.filename.substring(0, 50)}}... (${{(p.alignment * 100).toFixed(0)}}%)`
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
