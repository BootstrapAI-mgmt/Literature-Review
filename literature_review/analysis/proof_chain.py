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
            gap_data = json.load(f)
            # Transform gap data to expected format
            self.gap_data = self._transform_gap_data(gap_data)
        
        with open(pillar_definitions_file, 'r') as f:
            pillars_data = json.load(f)
            # Transform pillar data to list format
            self.pillars = self._transform_pillar_data(pillars_data)
        
        self.dependency_graph = nx.DiGraph()
    
    def _transform_gap_data(self, gap_data: Dict) -> Dict:
        """Transform gap data from nested dict to pillars array format."""
        pillars = []
        for pillar_name, pillar_data in gap_data.items():
            if not isinstance(pillar_data, dict):
                continue
            
            requirements = []
            analysis = pillar_data.get('analysis', {})
            
            for req_key, sub_reqs in analysis.items():
                for sub_req_key, sub_req_data in sub_reqs.items():
                    # Create a unique ID for this sub-requirement
                    req_id = f"{pillar_name.split(':')[0].strip()}-{req_key.split(':')[0].strip()}-{sub_req_key.split(':')[0].strip()}"
                    
                    completeness = sub_req_data.get('completeness_percent', 0)
                    papers = sub_req_data.get('contributing_papers', [])
                    
                    # Calculate gap severity based on completeness
                    if completeness >= 80:
                        gap_severity = 'Covered'
                    elif completeness >= 60:
                        gap_severity = 'Low'
                    elif completeness >= 40:
                        gap_severity = 'Medium'
                    elif completeness >= 20:
                        gap_severity = 'High'
                    else:
                        gap_severity = 'Critical'
                    
                    # Calculate average alignment (use completeness as proxy)
                    avg_alignment = completeness / 100.0
                    
                    requirements.append({
                        'id': req_id,
                        'requirement': sub_req_key,
                        'papers_found': len(papers),
                        'gap_severity': gap_severity,
                        'avg_alignment': avg_alignment
                    })
            
            pillars.append({
                'name': pillar_name,
                'requirements': requirements
            })
        
        return {'pillars': pillars}
    
    def _transform_pillar_data(self, pillars_data) -> List[Dict]:
        """Transform pillar data from nested dict to list format."""
        # If already in list format, return as-is
        if isinstance(pillars_data, list):
            return pillars_data
        
        pillars = []
        
        for pillar_name, pillar_content in pillars_data.items():
            if pillar_name == 'Framework_Overview':
                continue
            
            requirements = []
            pillar_reqs = pillar_content.get('requirements', {})
            
            for req_key, sub_req_list in pillar_reqs.items():
                if isinstance(sub_req_list, list):
                    for sub_req in sub_req_list:
                        # Create a unique ID
                        req_id = f"{pillar_name.split(':')[0].strip()}-{req_key.split(':')[0].strip()}-{sub_req.split(':')[0].strip()}"
                        
                        requirements.append({
                            'id': req_id,
                            'requirement': sub_req,
                            'depends_on': []  # Will be populated if dependencies exist
                        })
            
            pillars.append({
                'name': pillar_name,
                'requirements': requirements
            })
        
        return pillars
    
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
            if p['name'] == pillar or pillar.startswith(p['name'].split(':')[0]):
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
