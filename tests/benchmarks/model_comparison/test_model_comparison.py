"""
Model Comparison Benchmark Tests

Validates MC-01, MC-02, MC-03 from the validation matrix.
Compares LLM performance across providers for the same tasks.

Usage:
    # Compare specific models
    pytest tests/benchmarks/model_comparison/ --models gemini-flash,gpt-4-turbo
    
    # Run with default model only
    pytest tests/benchmarks/model_comparison/
"""

import json
import pytest
import time
from typing import List, Dict, Any
from dataclasses import dataclass

from literature_review.config.model_config import (
    get_model_by_name,
    ModelConfig,
    get_available_models,
    reset_model_config
)
from literature_review.utils.llm_client import get_llm_client


@dataclass
class ModelComparisonResult:
    """Result of a model comparison test."""
    model_name: str
    response: str
    latency_seconds: float
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    
    def __repr__(self):
        return (
            f"{self.model_name}: {self.latency_seconds:.2f}s, "
            f"${self.estimated_cost:.4f}, "
            f"{self.input_tokens}+{self.output_tokens} tokens"
        )


# Standard test prompts for comparison
TEST_PROMPTS = {
    "simple": "What is the capital of France?",
    "json_extraction": """Extract the following information as JSON:
        Paper: "Deep Learning for Neuromorphic Computing"
        Authors: John Smith, Jane Doe
        Year: 2024
        
        Return: {"title": ..., "authors": [...], "year": ...}
    """,
    "claim_analysis": """Analyze this scientific claim:
        "Spiking neural networks achieve 10x energy efficiency compared to traditional ANNs"
        
        Rate on a scale of 1-5 for:
        - Strength of evidence
        - Relevance to neuromorphic computing
        - Specificity of claim
    """,
}


@pytest.fixture(autouse=True)
def reset_model_state():
    """Reset model configuration before and after each test."""
    reset_model_config()
    yield
    reset_model_config()


class TestModelComparison:
    """MC-01, MC-02, MC-03: Model comparison benchmarks."""
    
    @pytest.fixture
    def test_models(self, request) -> List[str]:
        """Get list of models to compare."""
        models_opt = request.config.getoption("--models", default=None)
        if models_opt:
            return models_opt.split(",")
        return ["gemini-2.5-flash"]  # Default to single model
    
    @pytest.mark.benchmark
    @pytest.mark.requires_api
    def test_mc01_same_prompt_comparison(self, test_models: List[str]):
        """
        MC-01: Same-prompt response comparison across models.
        
        Verifies that different models produce semantically similar
        responses to the same prompt.
        """
        prompt = TEST_PROMPTS["simple"]
        results: List[ModelComparisonResult] = []
        
        for model_name in test_models:
            try:
                config = get_model_by_name(model_name)
                client = get_llm_client(config)
                
                start = time.time()
                response = client.generate(prompt)
                latency = time.time() - start
                
                tokens = client.get_token_counts()
                cost = config.estimate_cost(tokens["input"], tokens["output"])
                
                results.append(ModelComparisonResult(
                    model_name=model_name,
                    response=response,
                    latency_seconds=latency,
                    input_tokens=tokens["input"],
                    output_tokens=tokens["output"],
                    estimated_cost=cost
                ))
            except Exception as e:
                pytest.skip(f"Model {model_name} not available: {e}")
        
        # Log comparison
        for result in results:
            print(f"\n{result}")
            print(f"  Response: {result.response[:100]}...")
        
        # If multiple models, check semantic similarity
        if len(results) >= 2:
            # Basic check: all responses should mention "Paris"
            for result in results:
                assert "paris" in result.response.lower(), (
                    f"{result.model_name} did not mention Paris"
                )
    
    @pytest.mark.benchmark
    @pytest.mark.requires_api
    def test_mc02_cost_normalized_accuracy(self, test_models: List[str]):
        """
        MC-02: Cost-normalized accuracy comparison.
        
        Compares the cost/accuracy ratio across models for a structured task.
        """
        prompt = TEST_PROMPTS["json_extraction"]
        results: List[Dict[str, Any]] = []
        
        for model_name in test_models:
            try:
                config = get_model_by_name(model_name)
                client = get_llm_client(config)
                
                start = time.time()
                response = client.generate(prompt, json_mode=True)
                latency = time.time() - start
                
                tokens = client.get_token_counts()
                cost = config.estimate_cost(tokens["input"], tokens["output"])
                
                # Evaluate accuracy (did it extract correctly?)
                # Accuracy weights: title=1/3, authors=1/3, year=1/3
                ACCURACY_WEIGHT = 1.0 / 3.0
                try:
                    data = json.loads(response)
                    accuracy = 0.0
                    if data.get("title"):
                        accuracy += ACCURACY_WEIGHT
                    if data.get("authors") and len(data["authors"]) == 2:
                        accuracy += ACCURACY_WEIGHT
                    if data.get("year") == 2024:
                        accuracy += ACCURACY_WEIGHT
                except json.JSONDecodeError:
                    accuracy = 0.0
                
                results.append({
                    "model": model_name,
                    "accuracy": accuracy,
                    "cost": cost,
                    "latency": latency,
                    "cost_per_accuracy": cost / accuracy if accuracy > 0 else float('inf')
                })
                
            except Exception as e:
                pytest.skip(f"Model {model_name} not available: {e}")
        
        # Log results
        print("\nCost-Normalized Accuracy Comparison:")
        for r in sorted(results, key=lambda x: x["cost_per_accuracy"]):
            print(f"  {r['model']}: accuracy={r['accuracy']:.0%}, "
                  f"cost=${r['cost']:.4f}, ratio=${r['cost_per_accuracy']:.4f}/acc")
    
    @pytest.mark.benchmark
    @pytest.mark.requires_api
    def test_mc03_latency_comparison(self, test_models: List[str]):
        """
        MC-03: Latency comparison across models.
        
        Measures response time for each model on the same task.
        """
        prompt = TEST_PROMPTS["claim_analysis"]
        latencies: Dict[str, float] = {}
        
        for model_name in test_models:
            try:
                config = get_model_by_name(model_name)
                client = get_llm_client(config)
                
                # Warm-up call
                client.generate("Hello")
                
                # Timed call
                start = time.time()
                response = client.generate(prompt)
                latency = time.time() - start
                
                latencies[model_name] = latency
                
            except Exception as e:
                pytest.skip(f"Model {model_name} not available: {e}")
        
        # Log results
        print("\nLatency Comparison:")
        for model, latency in sorted(latencies.items(), key=lambda x: x[1]):
            print(f"  {model}: {latency:.2f}s")
        
        # All models should respond within reasonable time
        for model, latency in latencies.items():
            assert latency < 60, f"{model} latency {latency:.1f}s exceeds 60s limit"


class TestModelConfigUnit:
    """Unit tests for model configuration module."""
    
    def test_get_available_models_returns_list(self):
        """Verify that get_available_models returns a list of model names."""
        models = get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gemini-2.5-flash" in models
    
    def test_get_model_by_name_valid(self):
        """Verify that get_model_by_name returns a valid config."""
        config = get_model_by_name("gemini-2.5-flash")
        assert config is not None
        assert config.model_name == "gemini-2.5-flash"
        assert config.provider.value == "gemini"
    
    def test_get_model_by_name_invalid(self):
        """Verify that get_model_by_name raises for unknown model."""
        with pytest.raises(ValueError) as exc_info:
            get_model_by_name("nonexistent-model")
        assert "Unknown model" in str(exc_info.value)
    
    def test_model_config_estimate_cost(self):
        """Verify cost estimation works correctly."""
        config = get_model_by_name("gpt-4-turbo")
        # GPT-4 Turbo: $0.01/1K input, $0.03/1K output
        cost = config.estimate_cost(input_tokens=1000, output_tokens=500)
        expected = (1000 / 1000) * 0.01 + (500 / 1000) * 0.03  # $0.01 + $0.015 = $0.025
        assert abs(cost - expected) < 0.0001
    
    def test_model_aliases_work(self):
        """Verify that model aliases resolve correctly."""
        config1 = get_model_by_name("gemini-flash")
        config2 = get_model_by_name("gemini-2.5-flash")
        assert config1.model_name == config2.model_name
