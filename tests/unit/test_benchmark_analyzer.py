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


class TestGenerateBenchmarkMatrix:
    """Tests for the generate_benchmark_matrix convenience function."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 2: AI Stimulus-Response": {
                "quantitative_metrics": {
                    "latency_target": "< 10ms end-to-end",
                    "power_efficiency": "< 1W for 1M neurons"
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_generate_matrix_function(self, sample_pillar_definitions, tmp_path):
        """Test the convenience function."""
        paper_benchmarks = {
            "paper1.pdf": {
                "benchmarks_used": [
                    {
                        "name": "N-MNIST",
                        "type": "dataset",
                        "metrics_tested": ["accuracy"],
                        "measurement_method": "Top-1 classification"
                    }
                ],
                "metric_coverage": []
            }
        }
        output_path = str(tmp_path / "output_matrix.json")
        
        result = generate_benchmark_matrix(
            pillar_definitions_path=sample_pillar_definitions,
            paper_benchmarks=paper_benchmarks,
            output_path=output_path
        )
        
        assert Path(output_path).exists()
        assert "summary" in result
        assert "benchmark_inventory" in result
        assert "N-MNIST" in result["benchmark_inventory"]
