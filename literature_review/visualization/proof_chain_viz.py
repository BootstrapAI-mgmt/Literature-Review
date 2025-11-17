"""
Proof Chain Network Visualization
Generate interactive force-directed graph of requirement dependencies.
"""

import json
import os


def generate_proof_chain_html(report_file: str, output_file: str):
    """
    Generate force-directed graph visualization.
    
    Args:
        report_file: Path to proof chain analysis report
        output_file: Path for output HTML file
    """
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    graph_data = report['graph_data']
    blocking_reqs = report.get('blocking_requirements', [])
    priorities = report.get('prioritized_requirements', [])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Proof Chain Dependencies</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card h3 {{
            margin: 0;
            font-size: 2em;
            font-weight: bold;
        }}
        .stat-card p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
        .controls {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .controls label {{
            margin-right: 15px;
            font-weight: 600;
        }}
        .controls select, .controls button {{
            padding: 8px 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
            margin-right: 10px;
            cursor: pointer;
        }}
        .controls button {{
            background: #667eea;
            color: white;
            border: none;
            font-weight: 600;
        }}
        .controls button:hover {{
            background: #5568d3;
        }}
        .graph-container {{
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            background: #fafafa;
        }}
        .node {{
            stroke: #fff;
            stroke-width: 2px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .node:hover {{
            stroke-width: 4px;
            stroke: #667eea;
        }}
        .link {{
            stroke: #999;
            stroke-opacity: 0.4;
            fill: none;
        }}
        .link.highlighted {{
            stroke: #667eea;
            stroke-opacity: 0.8;
            stroke-width: 3px;
        }}
        .label {{
            font-size: 11px;
            pointer-events: none;
            fill: #333;
            font-weight: 500;
        }}
        .arrow {{
            fill: #999;
        }}
        .legend {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-circle {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid white;
        }}
        .info-panel {{
            position: fixed;
            right: 30px;
            top: 100px;
            width: 350px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: none;
        }}
        .info-panel.active {{
            display: block;
        }}
        .info-panel h3 {{
            margin-top: 0;
            color: #667eea;
        }}
        .info-panel .close {{
            position: absolute;
            top: 10px;
            right: 10px;
            cursor: pointer;
            font-size: 20px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 Proof Chain Dependencies</h1>
        
        <div class="stats">
            <div class="stat-card">
                <h3>{report['graph_stats']['total_requirements']}</h3>
                <p>Total Requirements</p>
            </div>
            <div class="stat-card">
                <h3>{report['graph_stats']['total_dependencies']}</h3>
                <p>Dependencies</p>
            </div>
            <div class="stat-card">
                <h3>{report['graph_stats']['critical_path_length']}</h3>
                <p>Critical Path Length</p>
            </div>
        </div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-circle" style="background: #dc3545;"></div>
                <span>Critical Gap</span>
            </div>
            <div class="legend-item">
                <div class="legend-circle" style="background: #fd7e14;"></div>
                <span>High Gap</span>
            </div>
            <div class="legend-item">
                <div class="legend-circle" style="background: #ffc107;"></div>
                <span>Medium Gap</span>
            </div>
            <div class="legend-item">
                <div class="legend-circle" style="background: #28a745;"></div>
                <span>Low Gap</span>
            </div>
            <div class="legend-item">
                <div class="legend-circle" style="background: #17a2b8;"></div>
                <span>Covered</span>
            </div>
            <div class="legend-item">
                <span>🔴 Blocking Requirements (3+ downstream)</span>
            </div>
        </div>
        
        <div class="controls">
            <label>Highlight:</label>
            <select id="highlight-mode">
                <option value="none">None</option>
                <option value="blocking">Blocking Requirements</option>
                <option value="critical-path">Critical Path</option>
                <option value="high-priority">High Priority</option>
            </select>
            
            <button id="zoom-fit">Fit to Screen</button>
            <button id="reset-positions">Reset Layout</button>
        </div>
        
        <div class="graph-container">
            <svg id="graph" width="1540" height="900"></svg>
        </div>
    </div>
    
    <div class="info-panel" id="info-panel">
        <span class="close" onclick="closeInfoPanel()">×</span>
        <h3 id="info-title">Requirement Details</h3>
        <div id="info-content"></div>
    </div>
    
    <script>
        const nodes = {json.dumps(graph_data['nodes'])};
        const links = {json.dumps(graph_data['edges'])};
        const blockingReqs = {json.dumps([b['requirement_id'] for b in blocking_reqs])};
        const criticalPath = {json.dumps(report['critical_paths'][0] if report['critical_paths'] else [])};
        const priorities = {json.dumps(priorities[:10])};
        
        const colorScale = {{
            'Critical': '#dc3545',
            'High': '#fd7e14',
            'Medium': '#ffc107',
            'Low': '#28a745',
            'Covered': '#17a2b8',
            'Unknown': '#6c757d'
        }};
        
        const width = 1540;
        const height = 900;
        
        const svg = d3.select("#graph");
        
        // Add zoom behavior
        const g = svg.append("g");
        
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});
        
        svg.call(zoom);
        
        // Define arrow markers
        svg.append("defs").selectAll("marker")
            .data(["arrow"])
            .join("marker")
            .attr("id", "arrow")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("class", "arrow");
        
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(50));
        
        const link = g.append("g")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("class", "link")
            .attr("marker-end", "url(#arrow)");
        
        const node = g.append("g")
            .selectAll("circle")
            .data(nodes)
            .join("circle")
            .attr("class", "node")
            .attr("r", d => {{
                const baseSize = 8 + Math.sqrt(d.papers) * 4;
                return blockingReqs.includes(d.id) ? baseSize + 5 : baseSize;
            }})
            .attr("fill", d => colorScale[d.gap_severity] || "#ccc")
            .attr("stroke-width", d => blockingReqs.includes(d.id) ? 4 : 2)
            .on("click", showNodeInfo)
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        const label = g.append("g")
            .selectAll("text")
            .data(nodes)
            .join("text")
            .attr("class", "label")
            .attr("text-anchor", "middle")
            .attr("dy", -15)
            .text(d => d.id);
        
        node.append("title")
            .text(d => `${{d.id}}\\n${{d.label}}\\nPapers: ${{d.papers}}\\nGap: ${{d.gap_severity}}`);
        
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        }});
        
        // Highlight mode
        d3.select("#highlight-mode").on("change", function() {{
            const mode = this.value;
            
            link.classed("highlighted", false);
            node.attr("opacity", 1);
            
            if (mode === "blocking") {{
                node.attr("opacity", d => blockingReqs.includes(d.id) ? 1 : 0.3);
            }} else if (mode === "critical-path") {{
                node.attr("opacity", d => criticalPath.includes(d.id) ? 1 : 0.3);
                link.classed("highlighted", d => 
                    criticalPath.includes(d.source.id) && criticalPath.includes(d.target.id)
                );
            }} else if (mode === "high-priority") {{
                const priorityIds = priorities.map(p => p.requirement_id);
                node.attr("opacity", d => priorityIds.includes(d.id) ? 1 : 0.3);
            }}
        }});
        
        // Zoom controls
        d3.select("#zoom-fit").on("click", () => {{
            const bounds = g.node().getBBox();
            const fullWidth = bounds.width;
            const fullHeight = bounds.height;
            const midX = bounds.x + fullWidth / 2;
            const midY = bounds.y + fullHeight / 2;
            
            const scale = 0.8 / Math.max(fullWidth / width, fullHeight / height);
            const translate = [width / 2 - scale * midX, height / 2 - scale * midY];
            
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
            );
        }});
        
        d3.select("#reset-positions").on("click", () => {{
            simulation.alpha(1).restart();
        }});
        
        function showNodeInfo(event, d) {{
            const panel = document.getElementById("info-panel");
            const title = document.getElementById("info-title");
            const content = document.getElementById("info-content");
            
            title.textContent = d.id;
            
            const isBlocking = blockingReqs.includes(d.id);
            const priority = priorities.find(p => p.requirement_id === d.id);
            
            content.innerHTML = `
                <p><strong>Requirement:</strong><br>${{d.label}}</p>
                <p><strong>Pillar:</strong> ${{d.pillar}}</p>
                <p><strong>Papers Found:</strong> ${{d.papers}}</p>
                <p><strong>Gap Severity:</strong> <span style="color: ${{colorScale[d.gap_severity]}}">${{d.gap_severity}}</span></p>
                ${{isBlocking ? '<p><strong>⚠️ Blocking Requirement</strong></p>' : ''}}
                ${{priority ? `<p><strong>Priority Score:</strong> ${{priority.priority_score}}</p>` : ''}}
            `;
            
            panel.classList.add("active");
        }}
        
        function closeInfoPanel() {{
            document.getElementById("info-panel").classList.remove("active");
        }}
        
        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }}
        
        function dragged(event) {{
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }}
        
        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }}
    </script>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Proof chain visualization saved to {output_file}")
