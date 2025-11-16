# Task Card: Proof Chain Dependencies

**Task ID:** ENHANCE-W2-2  
**Wave:** 2 (Deep Analysis)  
**Priority:** MEDIUM  
**Estimated Effort:** 12 hours  
**Status:** Not Started  
**Dependencies:** ENHANCE-W1-2 (Proof Scorecard)

---

## Objective

Map logical dependencies between requirements to identify critical bottlenecks blocking publication.

## Background

From Enhanced Analysis Proposal: Requirements form dependency chains where foundational claims must be proven before dependent claims. Need to visualize these chains and identify blocking requirements that prevent progression toward publication goals.

## Success Criteria

- [ ] Dependency graph showing requirement relationships
- [ ] Identify critical path to publication
- [ ] Identify blocking requirements (gates)
- [ ] Calculate "proof readiness" propagation through dependency chain
- [ ] Prioritize requirements based on downstream impact

## Deliverables

### 1. Proof Chain Analyzer

**File:** `literature_review/analysis/proof_chain.py`

```python
"""
Proof Chain Dependency Analysis
Map logical dependencies between requirements and identify bottlenecks.
"""

import json
import networkx as nx
from typing import Dict, List, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class ProofChainAnalyzer:
    """Analyze proof dependencies and critical paths."""
    
    def __init__(self, gap_analysis_file: str, pillar_definitions_file: str):
        self.gap_file = gap_analysis_file
        self.pillar_file = pillar_definitions_file
        
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
        
        with open(pillar_definitions_file, 'r') as f:
            self.pillars = json.load(f)
        
        self.dependency_graph = nx.DiGraph()
    
    def analyze_dependencies(self) -> Dict:
        """Perform complete dependency analysis."""
        logger.info("Analyzing proof chain dependencies...")
        
        # Build dependency graph
        self._build_dependency_graph()
        
        # Identify critical paths
        critical_paths = self._find_critical_paths()
        
        # Find blocking requirements
        blocking_reqs = self._find_blocking_requirements()
        
        # Calculate proof propagation
        proof_propagation = self._calculate_proof_propagation()
        
        # Prioritize requirements
        priorities = self._prioritize_requirements()
        
        return {
            'graph_stats': {
                'total_requirements': self.dependency_graph.number_of_nodes(),
                'total_dependencies': self.dependency_graph.number_of_edges(),
                'critical_path_length': len(critical_paths[0]) if critical_paths else 0
            },
            'critical_paths': critical_paths,
            'blocking_requirements': blocking_reqs,
            'proof_propagation': proof_propagation,
            'prioritized_requirements': priorities,
            'graph_data': self._export_graph_data()
        }
    
    def _build_dependency_graph(self):
        """Build requirement dependency graph from pillar definitions."""
        for pillar in self.pillars:
            pillar_name = pillar['name']
            
            for req in pillar.get('requirements', []):
                req_id = req['id']
                req_text = req['requirement']
                
                # Add node
                self.dependency_graph.add_node(
                    req_id,
                    pillar=pillar_name,
                    requirement=req_text,
                    gap_status=self._get_gap_status(req_id, pillar_name)
                )
                
                # Add dependency edges
                depends_on = req.get('depends_on', [])
                for dep_id in depends_on:
                    self.dependency_graph.add_edge(dep_id, req_id)
    
    def _get_gap_status(self, req_id: str, pillar: str) -> Dict:
        """Get gap analysis status for a requirement."""
        for p in self.gap_data['pillars']:
            if p['name'] == pillar:
                for r in p['requirements']:
                    if r['id'] == req_id:
                        return {
                            'papers_found': r['papers_found'],
                            'gap_severity': r['gap_severity'],
                            'avg_alignment': r.get('avg_alignment', 0.0)
                        }
        return {'papers_found': 0, 'gap_severity': 'Unknown', 'avg_alignment': 0.0}
    
    def _find_critical_paths(self) -> List[List[str]]:
        """Find critical paths (longest paths to terminal nodes)."""
        # Find source nodes (no predecessors)
        sources = [n for n in self.dependency_graph.nodes() 
                  if self.dependency_graph.in_degree(n) == 0]
        
        # Find sink nodes (no successors)
        sinks = [n for n in self.dependency_graph.nodes() 
                if self.dependency_graph.out_degree(n) == 0]
        
        critical_paths = []
        
        for source in sources:
            for sink in sinks:
                try:
                    paths = list(nx.all_simple_paths(self.dependency_graph, source, sink))
                    critical_paths.extend(paths)
                except nx.NetworkXNoPath:
                    pass
        
        # Sort by length (longest first)
        critical_paths.sort(key=len, reverse=True)
        
        return critical_paths[:5]  # Top 5 longest paths
    
    def _find_blocking_requirements(self) -> List[Dict]:
        """Find requirements that block many downstream requirements."""
        blocking = []
        
        for node in self.dependency_graph.nodes():
            # Count downstream nodes (transitive dependencies)
            descendants = nx.descendants(self.dependency_graph, node)
            
            if len(descendants) >= 3:  # Blocks 3+ requirements
                gap_status = self.dependency_graph.nodes[node]['gap_status']
                
                blocking.append({
                    'requirement_id': node,
                    'requirement': self.dependency_graph.nodes[node]['requirement'],
                    'pillar': self.dependency_graph.nodes[node]['pillar'],
                    'blocks_count': len(descendants),
                    'blocked_requirements': list(descendants),
                    'gap_status': gap_status,
                    'is_critical': gap_status['gap_severity'] in ['High', 'Critical']
                })
        
        # Sort by impact (blocks_count * criticality)
        blocking.sort(key=lambda x: x['blocks_count'], reverse=True)
        
        return blocking
    
    def _calculate_proof_propagation(self) -> Dict:
        """Calculate how proof readiness propagates through the chain."""
        propagation = {}
        
        # Topological sort (start from foundational requirements)
        try:
            topo_order = list(nx.topological_sort(self.dependency_graph))
        except nx.NetworkXError:
            # Graph has cycles
            logger.warning("Dependency graph has cycles - using approximate ordering")
            topo_order = list(self.dependency_graph.nodes())
        
        for node in topo_order:
            gap_status = self.dependency_graph.nodes[node]['gap_status']
            
            # Calculate readiness score (0-1)
            papers = gap_status['papers_found']
            quality = gap_status['avg_alignment']
            
            own_readiness = min(1.0, (papers / 10) * quality)
            
            # Propagate from dependencies
            predecessors = list(self.dependency_graph.predecessors(node))
            
            if predecessors:
                dep_readiness = [propagation[p]['propagated_readiness'] 
                               for p in predecessors if p in propagation]
                
                if dep_readiness:
                    # Minimum readiness from dependencies (chain is as weak as weakest link)
                    dependency_readiness = min(dep_readiness)
                    # Combined readiness
                    propagated = (own_readiness + dependency_readiness) / 2
                else:
                    propagated = own_readiness
            else:
                propagated = own_readiness
            
            propagation[node] = {
                'own_readiness': own_readiness,
                'propagated_readiness': propagated,
                'is_bottleneck': (own_readiness < 0.5 and len(list(self.dependency_graph.successors(node))) > 0)
            }
        
        return propagation
    
    def _prioritize_requirements(self) -> List[Dict]:
        """Prioritize requirements based on impact and readiness."""
        priorities = []
        
        for node in self.dependency_graph.nodes():
            descendants = nx.descendants(self.dependency_graph, node)
            gap_status = self.dependency_graph.nodes[node]['gap_status']
            
            # Priority score = downstream impact * (1 - current readiness)
            impact = len(descendants) + 1
            readiness = min(1.0, (gap_status['papers_found'] / 10) * gap_status['avg_alignment'])
            
            priority_score = impact * (1 - readiness)
            
            priorities.append({
                'requirement_id': node,
                'requirement': self.dependency_graph.nodes[node]['requirement'][:80],
                'priority_score': round(priority_score, 2),
                'impact': impact,
                'current_readiness': round(readiness, 2),
                'papers_found': gap_status['papers_found'],
                'gap_severity': gap_status['gap_severity']
            })
        
        priorities.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return priorities
    
    def _export_graph_data(self) -> Dict:
        """Export graph data for visualization."""
        nodes = []
        edges = []
        
        for node in self.dependency_graph.nodes():
            gap_status = self.dependency_graph.nodes[node]['gap_status']
            
            nodes.append({
                'id': node,
                'label': self.dependency_graph.nodes[node]['requirement'][:40] + '...',
                'pillar': self.dependency_graph.nodes[node]['pillar'],
                'papers': gap_status['papers_found'],
                'gap_severity': gap_status['gap_severity']
            })
        
        for source, target in self.dependency_graph.edges():
            edges.append({
                'source': source,
                'target': target
            })
        
        return {'nodes': nodes, 'edges': edges}


def generate_proof_chain_report(gap_file: str, pillar_file: str, 
                               output_file: str = 'gap_analysis_output/proof_chain.json'):
    """Generate proof chain dependency report."""
    import os
    
    analyzer = ProofChainAnalyzer(gap_file, pillar_file)
    report = analyzer.analyze_dependencies()
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Proof chain report saved to {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("PROOF CHAIN DEPENDENCY ANALYSIS")
    print("="*60)
    
    stats = report['graph_stats']
    print(f"\nGraph Statistics:")
    print(f"  Total Requirements: {stats['total_requirements']}")
    print(f"  Total Dependencies: {stats['total_dependencies']}")
    print(f"  Critical Path Length: {stats['critical_path_length']}")
    
    print(f"\n🚨 Blocking Requirements (Top 5):")
    for block in report['blocking_requirements'][:5]:
        print(f"  {block['requirement_id']}: {block['requirement'][:60]}...")
        print(f"    Blocks: {block['blocks_count']} requirements")
        print(f"    Gap: {block['gap_status']['gap_severity']}")
    
    print(f"\n🎯 Priority Requirements (Top 5):")
    for priority in report['prioritized_requirements'][:5]:
        print(f"  {priority['requirement_id']}: {priority['requirement']}")
        print(f"    Priority Score: {priority['priority_score']}, Readiness: {priority['current_readiness']}")
    
    print("\n" + "="*60)
    
    return report
```

### 2. Network Visualization (HTML)

**File:** `literature_review/visualization/proof_chain_viz.py`

```python
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
```

### 3. Integration with Gap Analysis

**File:** `DeepRequirementsAnalyzer.py` (additions)

```python
from literature_review.analysis.proof_chain import generate_proof_chain_report
from literature_review.visualization.proof_chain_viz import generate_proof_chain_html

class DeepRequirementsAnalyzer:
    def generate_outputs(self):
        """Generate all analysis outputs."""
        
        # ... existing outputs (gap analysis, waterfall charts, etc.) ...
        
        # NEW: Generate proof chain analysis
        logger.info("Analyzing proof chain dependencies...")
        generate_proof_chain_report(
            gap_file='gap_analysis_output/gap_analysis_report.json',
            pillar_file='pillar_definitions.json',
            output_file='gap_analysis_output/proof_chain.json'
        )
        
        # Generate interactive visualization
        generate_proof_chain_html(
            report_file='gap_analysis_output/proof_chain.json',
            output_file='gap_analysis_output/proof_chain.html'
        )
        
        logger.info("Proof chain analysis complete")
```

### 4. Pillar Definitions Enhancement

**Note:** Requires adding `depends_on` field to pillar definitions.

**Example Update to `pillar_definitions.json`:**

```json
{
  "name": "Pillar 1: Foundational Architecture",
  "requirements": [
    {
      "id": "P1-R1",
      "requirement": "Scalable microservices architecture",
      "depends_on": []
    },
    {
      "id": "P1-R2",
      "requirement": "API gateway with rate limiting",
      "depends_on": ["P1-R1"]
    },
    {
      "id": "P1-R3",
      "requirement": "Service mesh for inter-service communication",
      "depends_on": ["P1-R1", "P1-R2"]
    }
  ]
}
```

### 5. CLI Utility

**File:** `scripts/analyze_proof_chain.py`

```python
#!/usr/bin/env python3
"""
Analyze proof chain dependencies and generate reports.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.analysis.proof_chain import generate_proof_chain_report
from literature_review.visualization.proof_chain_viz import generate_proof_chain_html
import argparse


def main():
    parser = argparse.ArgumentParser(description='Analyze proof chain dependencies')
    parser.add_argument(
        '--gap-file',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis report'
    )
    parser.add_argument(
        '--pillar-file',
        default='pillar_definitions.json',
        help='Path to pillar definitions'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/proof_chain.json',
        help='Output file for analysis report'
    )
    parser.add_argument(
        '--viz',
        default='gap_analysis_output/proof_chain.html',
        help='Output file for visualization'
    )
    parser.add_argument(
        '--open',
        action='store_true',
        help='Open visualization in browser'
    )
    
    args = parser.parse_args()
    
    # Generate analysis
    print("Analyzing proof chain dependencies...")
    report = generate_proof_chain_report(
        gap_file=args.gap_file,
        pillar_file=args.pillar_file,
        output_file=args.output
    )
    
    # Generate visualization
    print("\nGenerating interactive visualization...")
    generate_proof_chain_html(
        report_file=args.output,
        output_file=args.viz
    )
    
    print(f"\n✅ Analysis complete!")
    print(f"   Report: {args.output}")
    print(f"   Visualization: {args.viz}")
    
    # Open in browser if requested
    if args.open:
        import webbrowser
        webbrowser.open(f'file://{os.path.abspath(args.viz)}')
        print(f"\n🌐 Opened visualization in browser")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_proof_chain.py`

```python
"""Unit tests for proof chain dependency analysis."""

import pytest
import tempfile
import json
import os
from literature_review.analysis.proof_chain import ProofChainAnalyzer


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
                        "requirement": "Test Requirement 1",
                        "papers_found": 5,
                        "gap_severity": "Medium",
                        "avg_alignment": 0.6
                    },
                    {
                        "id": "P1-R2",
                        "requirement": "Test Requirement 2",
                        "papers_found": 2,
                        "gap_severity": "High",
                        "avg_alignment": 0.4
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_pillar_data():
    """Sample pillar definitions with dependencies."""
    return [
        {
            "name": "Test Pillar",
            "requirements": [
                {
                    "id": "P1-R1",
                    "requirement": "Test Requirement 1",
                    "depends_on": []
                },
                {
                    "id": "P1-R2",
                    "requirement": "Test Requirement 2",
                    "depends_on": ["P1-R1"]
                },
                {
                    "id": "P1-R3",
                    "requirement": "Test Requirement 3",
                    "depends_on": ["P1-R2"]
                }
            ]
        }
    ]


def test_dependency_graph_construction(tmp_path, sample_gap_data, sample_pillar_data):
    """Test graph construction from pillar definitions."""
    # Create temp files
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    # Create analyzer
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    assert analyzer.dependency_graph.number_of_nodes() == 3
    assert analyzer.dependency_graph.number_of_edges() == 2


def test_critical_path_finding(tmp_path, sample_gap_data, sample_pillar_data):
    """Test critical path detection."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    critical_paths = analyzer._find_critical_paths()
    
    assert len(critical_paths) > 0
    assert len(critical_paths[0]) == 3  # Path: P1-R1 -> P1-R2 -> P1-R3


def test_blocking_requirements_detection(tmp_path, sample_gap_data, sample_pillar_data):
    """Test blocking requirement detection."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    report = analyzer.analyze_dependencies()
    
    # P1-R1 should not be blocking (only blocks 2 requirements, threshold is 3)
    blocking = report['blocking_requirements']
    assert len(blocking) == 0  # With only 3 nodes, none meet threshold


def test_proof_propagation(tmp_path, sample_gap_data, sample_pillar_data):
    """Test proof readiness propagation."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    propagation = analyzer._calculate_proof_propagation()
    
    assert 'P1-R1' in propagation
    assert 'own_readiness' in propagation['P1-R1']
    assert 0 <= propagation['P1-R1']['own_readiness'] <= 1


def test_priority_calculation(tmp_path, sample_gap_data, sample_pillar_data):
    """Test requirement prioritization."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    priorities = analyzer._prioritize_requirements()
    
    assert len(priorities) == 3
    assert all('priority_score' in p for p in priorities)
    # Priorities should be sorted (highest first)
    assert priorities[0]['priority_score'] >= priorities[-1]['priority_score']
```

### Integration Tests

```bash
# Test with real pillar definitions
python scripts/analyze_proof_chain.py --gap-file gap_analysis_output/gap_analysis_report.json --pillar-file pillar_definitions.json

# Verify output files created
ls -lh gap_analysis_output/proof_chain.json
ls -lh gap_analysis_output/proof_chain.html

# Open visualization
python scripts/analyze_proof_chain.py --open

# Check blocking requirements in output
cat gap_analysis_output/proof_chain.json | jq '.blocking_requirements | length'

# Check critical path length
cat gap_analysis_output/proof_chain.json | jq '.graph_stats.critical_path_length'
```

### Manual Testing Checklist

- [ ] Graph visualization renders correctly
- [ ] Nodes are color-coded by gap severity
- [ ] Blocking requirements are visually distinct (larger, thicker border)
- [ ] Arrows show dependency direction correctly
- [ ] Highlight modes work (blocking, critical path, high priority)
- [ ] Zoom and pan controls function properly
- [ ] Node click shows info panel
- [ ] Critical path is identified correctly
- [ ] Priority scores make sense (higher for more impactful requirements)

## Acceptance Criteria

- [ ] Dependency graph built correctly from pillar definitions
- [ ] Critical paths identified (longest paths to terminal nodes)
- [ ] Blocking requirements detected (block 3+ downstream requirements)
- [ ] Proof readiness propagation calculated (weakest link principle)
- [ ] Requirements prioritized by downstream impact
- [ ] Interactive visualization generated with D3.js
- [ ] Highlight modes functional (blocking, critical path, priority)
- [ ] Info panel displays requirement details on click
- [ ] Integration with gap analysis pipeline complete
- [ ] CLI tool works for standalone analysis

## Integration Points

- **Input Files:**
  - `gap_analysis_report.json` - for gap severity and paper counts
  - `pillar_definitions.json` - for requirement dependencies
  
- **Output Files:**
  - `gap_analysis_output/proof_chain.json` - analysis report
  - `gap_analysis_output/proof_chain.html` - interactive visualization
  
- **Integration:**
  - Called by `DeepRequirementsAnalyzer.generate_outputs()`
  - Requires `depends_on` field in pillar definitions
  - Uses `networkx` for graph analysis

## Performance Considerations

- **Graph complexity:** O(n²) for pairwise path finding
- **Recommended:** <100 requirements for interactive visualization
- **Large graphs:** Consider clustering or filtering

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 2 (Week 3-4)
