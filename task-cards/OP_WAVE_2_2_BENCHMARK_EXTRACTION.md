# Task Card: Benchmark Extraction & Linkage

**Task ID:** OP-W2-2  
**Wave:** 2 (Extraction Enhancement)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** OP-W1-1 (Schema Foundation)  
**Blocks:** OP-W3-1 (Validation Tracker)

---

## Objective

Extract benchmark usage from papers and link to requirement metrics, generating a `requirement_benchmark_matrix.json` that shows which performance targets have validated benchmarks and which have gaps.

## Background

Currently:
- `pillar_definitions_enhanced.json` has `quantitative_metrics` and `validation_criteria`
- No explicit linkage between specific metrics and benchmarks
- Gap analysis doesn't track benchmark coverage
- Cannot identify metrics with no validation strategy

This task:
- Extracts benchmark usage during deep review
- Links benchmarks to specific metrics in pillar definitions
- Generates coverage matrix showing validated vs unvalidated metrics
- Identifies metrics needing benchmark definition

## Success Criteria

- [ ] Benchmark extraction prompt added to deep review
- [ ] `benchmark_analyzer.py` module created
- [ ] Benchmark data conforms to schema (OP-W1-1)
- [ ] `requirement_benchmark_matrix.json` generated
- [ ] Integration with gap analysis for coverage tracking
- [ ] Unit tests cover extraction and analysis logic

---

## Deliverables

### 1. Benchmark Extraction Prompt

**File:** `literature_review/reviewers/prompts/benchmark_prompt.py`

```python
"""
Benchmark Extraction Prompts

These prompts extract benchmark usage and validation methodology
from research papers to link performance targets with evidence.
"""

BENCHMARK_EXTRACTION_PROMPT = """
You are analyzing a research paper to extract benchmark and validation information.
Your goal is to identify what benchmarks, datasets, and validation methods were used.

**Paper Context:**
{paper_summary}

**Focus on these metrics from our requirements:**
{target_metrics}

Extract the following benchmark information:

## 1. Benchmarks Used
List all standardized benchmarks, datasets, or test protocols used in this paper.

For each benchmark:
- **Name:** Official benchmark/dataset name
- **Type:** (dataset, protocol, hardware_test, comparison_baseline)
- **URL/Citation:** Reference for the benchmark
- **Metrics Tested:** What was measured on this benchmark?
- **Measurement Method:** How was it measured? (timing method, accuracy calculation, etc.)
- **Result Reported:** What was the result?

## 2. Hardware Platform
What hardware was used for benchmarking?
- Neuromorphic chip (Loihi, TrueNorth, SpiNNaker, etc.)
- GPU (type, memory)
- Custom hardware

## 3. Comparison Baselines
What was the paper compared against?
- Prior work references
- Standard baselines (ANN equivalent, etc.)
- Theoretical limits

## 4. Novel Metrics
Any metrics reported that aren't in standard benchmarks?
- Custom metrics defined by authors
- Domain-specific measurements

## 5. Metric Coverage
For each of our target metrics, does this paper provide validation?

Return as JSON:

```json
{{
  "benchmarks_used": [
    {{
      "name": "string",
      "type": "dataset|protocol|hardware_test|comparison_baseline",
      "url_or_citation": "string or null",
      "metrics_tested": ["string"],
      "measurement_method": "string",
      "results": {{
        "metric_name": "value"
      }}
    }}
  ],
  "hardware_platform": {{
    "type": "neuromorphic|gpu|cpu|custom",
    "details": "string",
    "relevant_specs": ["string"]
  }},
  "comparison_baselines": [
    {{
      "name": "string",
      "type": "prior_work|standard_baseline|theoretical",
      "citation": "string or null"
    }}
  ],
  "novel_metrics": [
    {{
      "name": "string",
      "definition": "string",
      "measurement_method": "string"
    }}
  ],
  "metric_coverage": [
    {{
      "target_metric": "string (from our requirements)",
      "is_covered": true/false,
      "benchmark_used": "string or null",
      "result_summary": "string or null",
      "coverage_quality": "direct|indirect|partial|none"
    }}
  ]
}}
```

Be specific about measurement methods. If a benchmark is mentioned but results aren't reported, note that.
"""


def format_benchmark_extraction_prompt(
    paper_summary: str,
    target_metrics: list
) -> str:
    """Format benchmark extraction prompt with context."""
    metrics_text = "\n".join([f"- {m}" for m in target_metrics])
    
    return BENCHMARK_EXTRACTION_PROMPT.format(
        paper_summary=paper_summary,
        target_metrics=metrics_text
    )


def get_pillar_metrics(pillar_name: str, pillar_definitions: dict) -> list:
    """Extract target metrics for a pillar from definitions."""
    metrics = []
    
    for key, pillar_data in pillar_definitions.items():
        if pillar_name in key or key in pillar_name:
            quant_metrics = pillar_data.get("quantitative_metrics", {})
            for metric_name, metric_value in quant_metrics.items():
                if isinstance(metric_value, dict):
                    target = metric_value.get("target_value", str(metric_value))
                else:
                    target = str(metric_value)
                metrics.append(f"{metric_name}: {target}")
    
    return metrics
```

### 2. Benchmark Analyzer Module

**File:** `literature_review/analysis/benchmark_analyzer.py`

```python
"""
Benchmark Analyzer Module

Analyzes benchmark coverage across requirements and generates
the requirement-benchmark matrix.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
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
        
        # Partial match (one contains the other)
        if m1 in m2 or m2 in m1:
            return True
        
        # Key term match
        key_terms = ["latency", "accuracy", "power", "efficiency", "sparsity", 
                     "energy", "capacity", "speed", "throughput"]
        for term in key_terms:
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
```

### 3. Deep Reviewer Integration

**File:** `literature_review/reviewers/deep_reviewer.py` (additions)

```python
# Add to imports
from literature_review.reviewers.prompts.benchmark_prompt import (
    format_benchmark_extraction_prompt,
    get_pillar_metrics
)

# Add method to DeepReviewer class
def extract_benchmarks(
    self,
    paper_text: str,
    paper_summary: str,
    filename: str,
    target_pillars: List[str]
) -> Dict:
    """
    Extract benchmark information from a paper.
    
    Args:
        paper_text: Full paper text
        paper_summary: Paper summary/abstract
        filename: Paper filename
        target_pillars: List of pillars this paper relates to
    
    Returns:
        Benchmark extraction data
    """
    # Get target metrics for relevant pillars
    target_metrics = []
    for pillar in target_pillars:
        target_metrics.extend(
            get_pillar_metrics(pillar, self.pillar_definitions)
        )
    
    if not target_metrics:
        logger.warning(f"No target metrics found for {filename}")
        return {}
    
    # Format prompt
    prompt = format_benchmark_extraction_prompt(
        paper_summary=paper_summary,
        target_metrics=target_metrics
    )
    
    try:
        response = self.api_manager.cached_api_call(
            prompt,
            use_cache=True,
            is_json=True,
            cache_prefix="benchmark"
        )
        
        if response:
            return self._validate_benchmark_response(response)
        
    except Exception as e:
        logger.error(f"Benchmark extraction failed for {filename}: {e}")
    
    return {}

def _validate_benchmark_response(self, response: Dict) -> Dict:
    """Validate and clean benchmark extraction response."""
    validated = {
        "benchmarks_used": [],
        "hardware_platform": response.get("hardware_platform", {}),
        "comparison_baselines": [],
        "novel_metrics": [],
        "metric_coverage": []
    }
    
    # Validate benchmarks
    for bm in response.get("benchmarks_used", []):
        if isinstance(bm, dict) and "name" in bm:
            validated["benchmarks_used"].append({
                "name": bm.get("name", "Unknown"),
                "type": bm.get("type", "dataset"),
                "url_or_citation": bm.get("url_or_citation"),
                "metrics_tested": bm.get("metrics_tested", []),
                "measurement_method": bm.get("measurement_method", ""),
                "results": bm.get("results", {})
            })
    
    # Validate baselines
    for bl in response.get("comparison_baselines", []):
        if isinstance(bl, dict) and "name" in bl:
            validated["comparison_baselines"].append(bl)
    
    # Validate novel metrics
    for nm in response.get("novel_metrics", []):
        if isinstance(nm, dict) and "name" in nm:
            validated["novel_metrics"].append(nm)
    
    # Validate metric coverage
    for mc in response.get("metric_coverage", []):
        if isinstance(mc, dict) and "target_metric" in mc:
            validated["metric_coverage"].append({
                "target_metric": mc.get("target_metric", ""),
                "is_covered": mc.get("is_covered", False),
                "benchmark_used": mc.get("benchmark_used"),
                "result_summary": mc.get("result_summary"),
                "coverage_quality": mc.get("coverage_quality", "none")
            })
    
    return validated
```

### 4. Orchestrator Integration

**File:** `literature_review/orchestrator.py` (additions)

```python
# Add to imports
from literature_review.analysis.benchmark_analyzer import (
    BenchmarkAnalyzer,
    generate_benchmark_matrix
)

# Add to orchestrator class
def generate_benchmark_coverage_matrix(
    self,
    output_path: Optional[str] = None
) -> Dict:
    """
    Generate benchmark coverage matrix from processed papers.
    
    Args:
        output_path: Optional custom output path
    
    Returns:
        Benchmark matrix dictionary
    """
    output_path = output_path or os.path.join(
        self.output_dir, "requirement_benchmark_matrix.json"
    )
    
    # Collect benchmark extractions from processed papers
    paper_benchmarks = {}
    
    for filename, paper_data in self.processed_papers.items():
        if "benchmark_extraction" in paper_data:
            paper_benchmarks[filename] = paper_data["benchmark_extraction"]
    
    if not paper_benchmarks:
        logger.warning("No benchmark data found in processed papers")
        return {}
    
    # Generate matrix
    matrix = generate_benchmark_matrix(
        pillar_definitions_path=self.pillar_definitions_path,
        paper_benchmarks=paper_benchmarks,
        output_path=output_path
    )
    
    logger.info(f"Generated benchmark matrix: {matrix['summary']}")
    return matrix
```

---

## Unit Tests

**File:** `tests/unit/test_benchmark_analyzer.py`

```python
"""Unit tests for benchmark analyzer."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from literature_review.analysis.benchmark_analyzer import (
    BenchmarkAnalyzer,
    BenchmarkCoverage,
    generate_benchmark_matrix
)
from literature_review.models import BenchmarkLink


class TestBenchmarkCoverage:
    """Tests for BenchmarkCoverage dataclass."""
    
    def test_create_coverage(self):
        """Test creating benchmark coverage."""
        coverage = BenchmarkCoverage(
            metric_id="P2-M1",
            metric_name="latency_target",
            target_value="< 10ms",
            pillar="Pillar 2",
            coverage_status="covered"
        )
        
        assert coverage.metric_id == "P2-M1"
        assert coverage.coverage_status == "covered"
    
    def test_coverage_with_benchmarks(self):
        """Test coverage with benchmark links."""
        coverage = BenchmarkCoverage(
            metric_id="P2-M1",
            metric_name="latency_target",
            target_value="< 10ms",
            pillar="Pillar 2",
            benchmarks=[
                BenchmarkLink(
                    benchmark_name="DVS128 Gesture",
                    benchmark_type="dataset",
                    metric_measured="latency",
                    measurement_method="Wall-clock timing"
                )
            ],
            evidence_papers=["paper1.pdf"],
            coverage_status="partial"
        )
        
        data = coverage.to_dict()
        assert len(data["benchmarks"]) == 1
        assert data["evidence_papers"] == ["paper1.pdf"]


class TestBenchmarkAnalyzer:
    """Tests for BenchmarkAnalyzer class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 2: AI Stimulus-Response": {
                "quantitative_metrics": {
                    "latency_target": "< 10ms end-to-end",
                    "power_efficiency": "< 1W for 1M neurons",
                    "sparsity": "< 10% average activation"
                }
            },
            "Pillar 4: AI Skill Automatization": {
                "quantitative_metrics": {
                    "compilation_efficiency": "> 90% reduction in inference time"
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_extract_all_metrics(self, sample_pillar_definitions):
        """Test extracting all metrics."""
        analyzer = BenchmarkAnalyzer(sample_pillar_definitions)
        metrics = analyzer._extract_all_metrics()
        
        assert len(metrics) == 4
        assert any("latency" in m["metric_name"] for m in metrics.values())
    
    def test_metrics_match(self, sample_pillar_definitions):
        """Test metric matching logic."""
        analyzer = BenchmarkAnalyzer(sample_pillar_definitions)
        
        assert analyzer._metrics_match("latency_target", "latency target")
        assert analyzer._metrics_match("power_efficiency", "power efficiency metric")
        assert analyzer._metrics_match("accuracy_rate", "classification accuracy")
        assert not analyzer._metrics_match("latency", "accuracy")
    
    def test_analyze_coverage_no_benchmarks(self, sample_pillar_definitions):
        """Test analysis with no benchmark data."""
        analyzer = BenchmarkAnalyzer(sample_pillar_definitions)
        result = analyzer.analyze_coverage()
        
        assert result["summary"]["total_metrics"] == 4
        assert result["summary"]["no_benchmark"] == 4
    
    def test_analyze_coverage_with_benchmarks(self, sample_pillar_definitions):
        """Test analysis with benchmark data."""
        analyzer = BenchmarkAnalyzer(sample_pillar_definitions)
        
        # Add benchmark extraction data
        analyzer.load_benchmark_extractions({
            "paper1.pdf": {
                "benchmarks_used": [
                    {
                        "name": "DVS128 Gesture",
                        "type": "dataset",
                        "metrics_tested": ["latency", "accuracy"],
                        "measurement_method": "Wall-clock timing"
                    }
                ],
                "metric_coverage": [
                    {
                        "target_metric": "latency target",
                        "is_covered": True,
                        "benchmark_used": "DVS128 Gesture",
                        "coverage_quality": "direct"
                    }
                ]
            }
        })
        
        result = analyzer.analyze_coverage()
        
        assert result["summary"]["no_benchmark"] < 4
        assert len(result["benchmark_inventory"]) > 0
    
    def test_identify_gaps(self, sample_pillar_definitions):
        """Test gap identification."""
        analyzer = BenchmarkAnalyzer(sample_pillar_definitions)
        result = analyzer.analyze_coverage()
        
        gaps = result["gaps_requiring_action"]
        assert len(gaps) > 0
        assert all("recommendation" in g for g in gaps)
    
    def test_save_matrix(self, sample_pillar_definitions, tmp_path):
        """Test saving matrix to file."""
        analyzer = BenchmarkAnalyzer(sample_pillar_definitions)
        output_path = str(tmp_path / "benchmark_matrix.json")
        
        matrix = analyzer.save_matrix(output_path)
        
        assert Path(output_path).exists()
        with open(output_path) as f:
            saved = json.load(f)
        assert saved["summary"]["total_metrics"] == 4


class TestBenchmarkPrompts:
    """Tests for benchmark extraction prompts."""
    
    def test_format_prompt(self):
        """Test prompt formatting."""
        from literature_review.reviewers.prompts.benchmark_prompt import (
            format_benchmark_extraction_prompt
        )
        
        prompt = format_benchmark_extraction_prompt(
            paper_summary="This paper presents an SNN...",
            target_metrics=["latency_target: < 10ms", "accuracy: > 95%"]
        )
        
        assert "latency_target" in prompt
        assert "accuracy" in prompt
        assert "Benchmarks Used" in prompt
    
    def test_get_pillar_metrics(self):
        """Test extracting pillar metrics."""
        from literature_review.reviewers.prompts.benchmark_prompt import get_pillar_metrics
        
        definitions = {
            "Pillar 2: AI Stimulus-Response": {
                "quantitative_metrics": {
                    "latency": "< 10ms"
                }
            }
        }
        
        metrics = get_pillar_metrics("Pillar 2", definitions)
        assert len(metrics) == 1
        assert "latency" in metrics[0]
```

---

## Acceptance Criteria Checklist

- [ ] Benchmark extraction prompt covers all required fields
- [ ] BenchmarkAnalyzer extracts metrics from pillar definitions
- [ ] Metric matching handles various naming conventions
- [ ] Coverage status correctly determined (covered/partial/no_benchmark)
- [ ] Gap identification generates actionable recommendations
- [ ] Benchmark inventory aggregates across papers
- [ ] Matrix saved in correct JSON format
- [ ] Integration with deep reviewer works
- [ ] Unit tests pass with >90% coverage
- [ ] Output integrates with gap analysis workflow

---

## Output Schema: `requirement_benchmark_matrix.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "summary": {
    "total_metrics": 42,
    "fully_covered": 28,
    "partially_covered": 8,
    "no_benchmark": 6,
    "coverage_percentage": 76.2
  },
  "coverage_by_pillar": {
    "Pillar 2: AI Stimulus-Response": [
      {
        "metric_id": "P2-M1",
        "metric_name": "latency_target",
        "target_value": "< 10ms end-to-end",
        "pillar": "Pillar 2: AI Stimulus-Response",
        "benchmarks": [
          {
            "benchmark_name": "DVS128 Gesture",
            "benchmark_type": "dataset",
            "metric_measured": "latency_target",
            "measurement_method": "End-to-end inference timing"
          }
        ],
        "evidence_papers": ["paper1.pdf", "paper2.pdf"],
        "coverage_status": "covered"
      }
    ]
  },
  "gaps_requiring_action": [
    {
      "metric_id": "P2-M2",
      "metric_name": "power_efficiency",
      "pillar": "Pillar 2: AI Stimulus-Response",
      "issue": "no_benchmark",
      "gap_notes": "No benchmark found for metric 'power_efficiency'",
      "recommendation": "Search for hardware power measurement studies on Loihi, SpiNNaker, TrueNorth",
      "priority": "HIGH"
    }
  ],
  "benchmark_inventory": {
    "DVS128 Gesture": {
      "name": "DVS128 Gesture",
      "type": "dataset",
      "url": "https://research.ibm.com/dvsgesture",
      "metrics_tested": ["accuracy", "latency", "power"],
      "papers_using": ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
    }
  }
}
```

---

## Notes for Agent

1. **Create prompts package:**
   ```bash
   mkdir -p literature_review/reviewers/prompts
   touch literature_review/reviewers/prompts/__init__.py
   ```

2. **Run analyzer standalone for testing:**
   ```python
   from literature_review.analysis.benchmark_analyzer import BenchmarkAnalyzer
   
   analyzer = BenchmarkAnalyzer("pillar_definitions_enhanced.json")
   result = analyzer.analyze_coverage()
   print(json.dumps(result["summary"], indent=2))
   ```

3. **Integration with Wave 3:**
   - Benchmark matrix feeds into validation_tracker.py (OP-W3-1)
   - Gap recommendations feed into search optimizer
