"""
Benchmark Analyzer Module

Analyzes benchmark coverage across requirements and generates
the requirement-benchmark matrix.
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
from datetime import datetime

from literature_review.models import (
    BenchmarkLink,
    MetricDefinition,
    ValidationStatus
)

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCoverage:
    """Coverage analysis for a single metric."""
    metric_id: str
    metric_name: str
    target_value: str
    pillar: str
    benchmarks: List[BenchmarkLink] = field(default_factory=list)
    evidence_papers: List[str] = field(default_factory=list)
    coverage_status: str = "no_benchmark"  # covered, partial, no_benchmark
    gap_notes: str = ""
    suggested_approach: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "target_value": self.target_value,
            "pillar": self.pillar,
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "evidence_papers": self.evidence_papers,
            "coverage_status": self.coverage_status,
            "gap_notes": self.gap_notes,
            "suggested_approach": self.suggested_approach
        }


class BenchmarkAnalyzer:
    """
    Analyze benchmark coverage across requirements.
    
    This class processes benchmark extraction data from papers and
    generates a matrix showing which metrics have validated benchmarks.
    """
    
    def __init__(
        self,
        pillar_definitions_path: str,
        version_history_path: Optional[str] = None
    ):
        """
        Initialize analyzer.
        
        Args:
            pillar_definitions_path: Path to pillar_definitions_enhanced.json
            version_history_path: Optional path to review_version_history.json
        """
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        self.version_history = {}
        if version_history_path and Path(version_history_path).exists():
            with open(version_history_path, 'r', encoding='utf-8') as f:
                self.version_history = json.load(f)
        
        # Extracted benchmark data from papers
        self.paper_benchmarks: Dict[str, Dict] = {}
        
        # Analysis results
        self.metric_coverage: Dict[str, BenchmarkCoverage] = {}
    
    def load_benchmark_extractions(self, extractions: Dict[str, Dict]):
        """
        Load benchmark extraction data from papers.
        
        Args:
            extractions: Dict mapping filename to benchmark extraction data
        """
        self.paper_benchmarks.update(extractions)
        logger.info(f"Loaded benchmark data from {len(extractions)} papers")
    
    def analyze_coverage(self) -> Dict:
        """
        Analyze benchmark coverage for all metrics.
        
        Returns:
            Coverage analysis dictionary
        """
        logger.info("Analyzing benchmark coverage...")
        
        # Extract all metrics from pillar definitions
        all_metrics = self._extract_all_metrics()
        logger.info(f"Found {len(all_metrics)} metrics to analyze")
        
        # Match benchmarks to metrics
        for metric_id, metric_info in all_metrics.items():
            coverage = self._analyze_metric_coverage(metric_id, metric_info)
            self.metric_coverage[metric_id] = coverage
        
        # Generate summary
        summary = self._generate_summary()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "coverage_by_pillar": self._group_by_pillar(),
            "gaps_requiring_action": self._identify_gaps(),
            "benchmark_inventory": self._build_benchmark_inventory()
        }
    
    def _extract_all_metrics(self) -> Dict[str, Dict]:
        """Extract all metrics from pillar definitions."""
        metrics = {}
        metric_counter = defaultdict(int)
        
        for pillar_name, pillar_data in self.pillar_definitions.items():
            if not pillar_name.startswith("Pillar"):
                continue
            
            quant_metrics = pillar_data.get("quantitative_metrics", {})
            pillar_num = pillar_name.split(":")[0].strip().replace("Pillar ", "P")
            
            for metric_name, metric_value in quant_metrics.items():
                metric_counter[pillar_num] += 1
                metric_id = f"{pillar_num}-M{metric_counter[pillar_num]}"
                
                # Handle both old and new formats
                if isinstance(metric_value, dict):
                    target = metric_value.get("target_value", str(metric_value))
                    existing_benchmarks = metric_value.get("benchmarks", [])
                else:
                    target = str(metric_value)
                    existing_benchmarks = []
                
                metrics[metric_id] = {
                    "metric_name": metric_name,
                    "target_value": target,
                    "pillar": pillar_name,
                    "existing_benchmarks": existing_benchmarks
                }
        
        return metrics
    
    def _analyze_metric_coverage(
        self,
        metric_id: str,
        metric_info: Dict
    ) -> BenchmarkCoverage:
        """Analyze benchmark coverage for a single metric."""
        metric_name = metric_info["metric_name"]
        target_value = metric_info["target_value"]
        pillar = metric_info["pillar"]
        
        # Find papers that tested this metric
        matching_benchmarks = []
        evidence_papers = []
        
        for paper_file, paper_data in self.paper_benchmarks.items():
            metric_coverage = paper_data.get("metric_coverage", [])
            
            for coverage in metric_coverage:
                # Match by metric name (fuzzy matching)
                if self._metrics_match(metric_name, coverage.get("target_metric", "")):
                    if coverage.get("is_covered"):
                        evidence_papers.append(paper_file)
                        
                        benchmark_name = coverage.get("benchmark_used")
                        if benchmark_name:
                            # Find full benchmark info
                            for bm in paper_data.get("benchmarks_used", []):
                                if bm.get("name") == benchmark_name:
                                    matching_benchmarks.append(BenchmarkLink(
                                        benchmark_name=bm["name"],
                                        benchmark_type=bm.get("type", "dataset"),
                                        metric_measured=metric_name,
                                        measurement_method=bm.get("measurement_method", ""),
                                        notes=coverage.get("result_summary")
                                    ))
        
        # Determine coverage status
        if len(matching_benchmarks) >= 2:
            coverage_status = "covered"
        elif len(matching_benchmarks) == 1:
            coverage_status = "partial"
        else:
            coverage_status = "no_benchmark"
        
        # Generate gap notes and suggestions
        gap_notes = ""
        suggested_approach = ""
        
        if coverage_status == "no_benchmark":
            gap_notes = f"No benchmark found for metric '{metric_name}'"
            suggested_approach = self._suggest_benchmark_approach(metric_name, pillar)
        elif coverage_status == "partial":
            gap_notes = "Only one benchmark source found - needs independent validation"
            suggested_approach = "Search for additional papers using this benchmark"
        
        return BenchmarkCoverage(
            metric_id=metric_id,
            metric_name=metric_name,
            target_value=target_value,
            pillar=pillar,
            benchmarks=matching_benchmarks,
            evidence_papers=evidence_papers,
            coverage_status=coverage_status,
            gap_notes=gap_notes,
            suggested_approach=suggested_approach
        )
    
    def _metrics_match(self, metric_name: str, target_metric: str) -> bool:
        """Check if two metric names match (fuzzy)."""
        # Normalize names
        m1 = metric_name.lower().replace("_", " ").replace("-", " ")
        m2 = target_metric.lower().replace("_", " ").replace("-", " ")
        
        # Exact match
        if m1 == m2:
            return True
        
        # Word-based matching to reduce false positives
        # Split into words and check for overlap
        words1 = set(m1.split())
        words2 = set(m2.split())
        
        # One is fully contained in the other as a word sequence
        if m1 in m2 or m2 in m1:
            # Ensure at least 3 chars to avoid trivial matches
            if len(m1) >= 3 and len(m2) >= 3:
                return True
        
        # Key term match - both must contain the same key term as a word
        key_terms = ["latency", "accuracy", "power", "efficiency", "sparsity", 
                     "energy", "capacity", "speed", "throughput"]
        for term in key_terms:
            # Check if term appears as a word (not substring)
            if term in words1 and term in words2:
                return True
            # Also check if term is a substring in both with word boundaries
            if term in m1 and term in m2:
                return True
        
        return False
    
    def _suggest_benchmark_approach(self, metric_name: str, pillar: str) -> str:
        """Generate suggested approach for finding benchmarks."""
        suggestions = {
            "latency": "Search for inference timing benchmarks on standard datasets (N-MNIST, DVS Gesture)",
            "accuracy": "Look for classification benchmarks on neuromorphic datasets",
            "power": "Search for hardware power measurement studies on Loihi, SpiNNaker, TrueNorth",
            "efficiency": "Look for energy-per-inference comparisons with ANN baselines",
            "sparsity": "Search for activation sparsity measurements during inference",
            "capacity": "Look for continual learning benchmarks (Split-MNIST, CORe50)",
            "speed": "Search for throughput benchmarks on neuromorphic hardware"
        }
        
        for term, suggestion in suggestions.items():
            if term in metric_name.lower():
                return suggestion
        
        return f"Search for standardized benchmarks for {metric_name} in {pillar.split(':')[0]}"
    
    def _generate_summary(self) -> Dict:
        """Generate coverage summary statistics."""
        total = len(self.metric_coverage)
        covered = sum(1 for c in self.metric_coverage.values() if c.coverage_status == "covered")
        partial = sum(1 for c in self.metric_coverage.values() if c.coverage_status == "partial")
        no_benchmark = sum(1 for c in self.metric_coverage.values() if c.coverage_status == "no_benchmark")
        
        return {
            "total_metrics": total,
            "fully_covered": covered,
            "partially_covered": partial,
            "no_benchmark": no_benchmark,
            "coverage_percentage": round((covered + partial * 0.5) / total * 100, 1) if total > 0 else 0
        }
    
    def _group_by_pillar(self) -> Dict:
        """Group coverage by pillar."""
        by_pillar = defaultdict(list)
        
        for metric_id, coverage in self.metric_coverage.items():
            by_pillar[coverage.pillar].append(coverage.to_dict())
        
        return dict(by_pillar)
    
    def _identify_gaps(self) -> List[Dict]:
        """Identify gaps requiring action."""
        gaps = []
        
        for metric_id, coverage in self.metric_coverage.items():
            if coverage.coverage_status in ["no_benchmark", "partial"]:
                gaps.append({
                    "metric_id": metric_id,
                    "metric_name": coverage.metric_name,
                    "pillar": coverage.pillar,
                    "issue": coverage.coverage_status,
                    "gap_notes": coverage.gap_notes,
                    "recommendation": coverage.suggested_approach,
                    "priority": "HIGH" if coverage.coverage_status == "no_benchmark" else "MEDIUM"
                })
        
        # Sort by priority
        return sorted(gaps, key=lambda x: (x["priority"] != "HIGH", x["pillar"]))
    
    def _build_benchmark_inventory(self) -> Dict:
        """Build inventory of all benchmarks found."""
        inventory = {}
        
        for paper_file, paper_data in self.paper_benchmarks.items():
            for bm in paper_data.get("benchmarks_used", []):
                bm_name = bm.get("name", "Unknown")
                
                if bm_name not in inventory:
                    inventory[bm_name] = {
                        "name": bm_name,
                        "type": bm.get("type", "unknown"),
                        "url": bm.get("url_or_citation"),
                        "metrics_tested": [],
                        "papers_using": []
                    }
                
                inventory[bm_name]["papers_using"].append(paper_file)
                inventory[bm_name]["metrics_tested"].extend(bm.get("metrics_tested", []))
        
        # Deduplicate metrics
        for bm_name in inventory:
            inventory[bm_name]["metrics_tested"] = list(set(inventory[bm_name]["metrics_tested"]))
        
        return inventory
    
    def save_matrix(self, output_path: str):
        """Save the benchmark matrix to file."""
        matrix = self.analyze_coverage()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved benchmark matrix to {output_path}")
        return matrix


def generate_benchmark_matrix(
    pillar_definitions_path: str,
    paper_benchmarks: Dict[str, Dict],
    output_path: str
) -> Dict:
    """
    Convenience function to generate benchmark matrix.
    
    Args:
        pillar_definitions_path: Path to pillar definitions
        paper_benchmarks: Dict of paper filename to benchmark data
        output_path: Path to save output matrix
    
    Returns:
        Generated matrix dictionary
    """
    analyzer = BenchmarkAnalyzer(pillar_definitions_path)
    analyzer.load_benchmark_extractions(paper_benchmarks)
    return analyzer.save_matrix(output_path)
