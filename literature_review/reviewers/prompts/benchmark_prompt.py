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
