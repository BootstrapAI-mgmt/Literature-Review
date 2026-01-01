# Task Card: Model Abstraction Layer

**Task ID:** VM-W0.5-3  
**Wave:** 0.5 (Modularization Infrastructure)  
**Priority:** HIGH (P3 - Highest effort, enables LLM comparison)  
**Estimated Effort:** 12 hours  
**Status:** Not Started  
**Dependencies:** None (can start in parallel)  
**Blocks:** Model comparison benchmarks (MC-01, MC-02, MC-03)  
**Validation IDs:** MC-01, MC-02, MC-03

---

## Objective

Create a model abstraction layer that enables the pipeline to be configured with different LLM providers (Gemini, OpenAI, Anthropic, local) without code changes, supporting model comparison benchmarks and provider-agnostic testing.

## Background

The third-party modularization assessment (Score: 3/10) identified that `gemini-2.5-flash` is hardcoded in multiple locations:

```python
# Current: Hardcoded in 6+ files
model="gemini-2.5-flash",  # api_manager.py line 130
model="gemini-2.5-flash",  # journal_reviewer.py line 282
model="gemini-2.5-flash",  # deep_reviewer.py line 204
model="gemini-2.5-flash",  # orchestrator.py line 412
```

This prevents:
- Benchmarking the same pipeline with different models (GPT-4, Claude, Gemini Pro)
- A/B testing model performance
- Cost-normalized accuracy comparison across providers
- Using local models (Ollama) for development

## Success Criteria

- [ ] MC-01: Same-prompt response comparison works across models
- [ ] MC-02: Cost-normalized accuracy comparison implemented
- [ ] MC-03: Latency comparison across models tracked
- [ ] `ModelConfig` abstraction supports Gemini, OpenAI, Anthropic
- [ ] `--model` CLI flag available in pipeline_orchestrator.py
- [ ] Model can be switched via environment variable
- [ ] Existing hardcoded calls migrated to use abstraction

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| MC-01 | Same-Prompt Comparison | Identical prompt to 2+ models | Response similarity | Similarity >80% (semantic) |
| MC-02 | Cost-Normalized Accuracy | Model results + costs | Cost/accuracy ratio | Ratio tracked per model |
| MC-03 | Latency Comparison | Timed API calls | Per-model latency | Latency baseline established |

---

## Deliverables

### 1. Model Configuration Module

**File:** `literature_review/config/model_config.py`

```python
"""
Model Abstraction Layer

Provides a unified interface for configuring and switching between LLM providers:
- Gemini (Google)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Local (Ollama, llama.cpp)

Usage:
    from literature_review.config.model_config import get_model_config, set_model
    
    # Use default (gemini-2.5-flash)
    config = get_model_config()
    
    # Switch to a different model
    set_model("gpt-4-turbo")
    
    # Or configure via environment
    # MODEL_NAME=claude-3-opus python pipeline_orchestrator.py
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Provider Definitions
# =============================================================================

class ModelProvider(Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # Ollama, llama.cpp, etc.


# =============================================================================
# Model Configuration
# =============================================================================

@dataclass
class ModelConfig:
    """
    LLM Configuration for pipeline operations.
    
    Encapsulates all model-specific settings including:
    - Provider and model name
    - API authentication
    - Generation parameters
    - Pricing for cost tracking
    - Provider-specific capabilities
    """
    provider: ModelProvider
    model_name: str
    api_key_env: str
    
    # Generation parameters
    temperature: float = 0.2
    max_tokens: int = 16384
    top_p: float = 1.0
    top_k: int = 1
    
    # Pricing for cost benchmarks (per 1K tokens)
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    
    # Provider-specific capabilities
    supports_json_mode: bool = True
    supports_system_prompt: bool = True
    supports_thinking_mode: bool = False
    max_context_length: int = 128000
    
    # Display name
    display_name: str = ""
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.model_name
    
    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment."""
        return os.environ.get(self.api_key_env)
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.api_key:
            logger.warning(f"API key not set: {self.api_key_env}")
            return False
        return True
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a given token count."""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost


# =============================================================================
# Pre-defined Model Configurations
# =============================================================================

class Models:
    """Pre-defined model configurations."""
    
    @staticmethod
    def gemini_flash() -> ModelConfig:
        """Gemini 2.5 Flash - Default, fast and free."""
        return ModelConfig(
            provider=ModelProvider.GEMINI,
            model_name="gemini-2.5-flash",
            api_key_env="GEMINI_API_KEY",
            display_name="Gemini 2.5 Flash",
            temperature=0.2,
            max_tokens=16384,
            input_cost_per_1k=0.0,  # Free tier
            output_cost_per_1k=0.0,
            supports_json_mode=True,
            supports_thinking_mode=True,
            max_context_length=1000000
        )
    
    @staticmethod
    def gemini_pro() -> ModelConfig:
        """Gemini 1.5 Pro - Higher quality, paid."""
        return ModelConfig(
            provider=ModelProvider.GEMINI,
            model_name="gemini-1.5-pro",
            api_key_env="GEMINI_API_KEY",
            display_name="Gemini 1.5 Pro",
            temperature=0.2,
            max_tokens=16384,
            input_cost_per_1k=0.00125,
            output_cost_per_1k=0.005,
            supports_json_mode=True,
            max_context_length=2000000
        )
    
    @staticmethod
    def gpt4_turbo() -> ModelConfig:
        """GPT-4 Turbo - OpenAI's best model."""
        return ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4-turbo",
            api_key_env="OPENAI_API_KEY",
            display_name="GPT-4 Turbo",
            temperature=0.2,
            max_tokens=4096,
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            supports_json_mode=True,
            max_context_length=128000
        )
    
    @staticmethod
    def gpt4o() -> ModelConfig:
        """GPT-4o - OpenAI's multimodal model."""
        return ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            display_name="GPT-4o",
            temperature=0.2,
            max_tokens=4096,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            supports_json_mode=True,
            max_context_length=128000
        )
    
    @staticmethod
    def gpt35_turbo() -> ModelConfig:
        """GPT-3.5 Turbo - Fast and cheap."""
        return ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key_env="OPENAI_API_KEY",
            display_name="GPT-3.5 Turbo",
            temperature=0.2,
            max_tokens=4096,
            input_cost_per_1k=0.0005,
            output_cost_per_1k=0.0015,
            supports_json_mode=True,
            max_context_length=16385
        )
    
    @staticmethod
    def claude_opus() -> ModelConfig:
        """Claude 3 Opus - Anthropic's most capable."""
        return ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            api_key_env="ANTHROPIC_API_KEY",
            display_name="Claude 3 Opus",
            temperature=0.2,
            max_tokens=4096,
            input_cost_per_1k=0.015,
            output_cost_per_1k=0.075,
            supports_json_mode=False,  # Uses XML-like format
            max_context_length=200000
        )
    
    @staticmethod
    def claude_sonnet() -> ModelConfig:
        """Claude 3.5 Sonnet - Balanced performance/cost."""
        return ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            api_key_env="ANTHROPIC_API_KEY",
            display_name="Claude 3.5 Sonnet",
            temperature=0.2,
            max_tokens=8192,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            supports_json_mode=False,
            max_context_length=200000
        )
    
    @staticmethod
    def claude_haiku() -> ModelConfig:
        """Claude 3 Haiku - Fast and cheap."""
        return ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
            api_key_env="ANTHROPIC_API_KEY",
            display_name="Claude 3 Haiku",
            temperature=0.2,
            max_tokens=4096,
            input_cost_per_1k=0.00025,
            output_cost_per_1k=0.00125,
            supports_json_mode=False,
            max_context_length=200000
        )
    
    @staticmethod
    def ollama_llama() -> ModelConfig:
        """Ollama Llama 3 - Local model."""
        return ModelConfig(
            provider=ModelProvider.LOCAL,
            model_name="llama3:8b",
            api_key_env="OLLAMA_HOST",  # localhost:11434
            display_name="Llama 3 (8B)",
            temperature=0.2,
            max_tokens=4096,
            input_cost_per_1k=0.0,  # Free (local)
            output_cost_per_1k=0.0,
            supports_json_mode=True,
            max_context_length=8192
        )


# =============================================================================
# Model Registry
# =============================================================================

MODEL_REGISTRY: Dict[str, Callable[[], ModelConfig]] = {
    # Gemini models
    "gemini-2.5-flash": Models.gemini_flash,
    "gemini-flash": Models.gemini_flash,  # Alias
    "gemini-1.5-pro": Models.gemini_pro,
    "gemini-pro": Models.gemini_pro,  # Alias
    
    # OpenAI models
    "gpt-4-turbo": Models.gpt4_turbo,
    "gpt-4o": Models.gpt4o,
    "gpt-3.5-turbo": Models.gpt35_turbo,
    
    # Anthropic models
    "claude-3-opus": Models.claude_opus,
    "claude-opus": Models.claude_opus,  # Alias
    "claude-3.5-sonnet": Models.claude_sonnet,
    "claude-sonnet": Models.claude_sonnet,  # Alias
    "claude-3-haiku": Models.claude_haiku,
    "claude-haiku": Models.claude_haiku,  # Alias
    
    # Local models
    "llama3:8b": Models.ollama_llama,
    "ollama-llama": Models.ollama_llama,  # Alias
}


def get_available_models() -> list:
    """Get list of available model names."""
    return sorted(set(MODEL_REGISTRY.keys()))


def get_model_by_name(name: str) -> ModelConfig:
    """Get a model configuration by name."""
    if name not in MODEL_REGISTRY:
        available = ", ".join(get_available_models())
        raise ValueError(f"Unknown model: {name}. Available: {available}")
    return MODEL_REGISTRY[name]()


# =============================================================================
# Global Configuration State
# =============================================================================

_current_model: Optional[ModelConfig] = None


def set_model(model_name: str) -> ModelConfig:
    """Set the current model by name."""
    global _current_model
    _current_model = get_model_by_name(model_name)
    logger.info(f"Model set to: {_current_model.display_name}")
    return _current_model


def set_model_config(config: ModelConfig) -> None:
    """Set the current model using a config object."""
    global _current_model
    _current_model = config
    logger.info(f"Model set to: {config.display_name}")


def get_model_config() -> ModelConfig:
    """
    Get the current model configuration.
    
    Resolution order:
    1. Explicitly set model (via set_model)
    2. MODEL_NAME environment variable
    3. Default (gemini-2.5-flash)
    """
    global _current_model
    
    if _current_model is not None:
        return _current_model
    
    # Check environment variable
    env_model = os.environ.get("MODEL_NAME")
    if env_model:
        try:
            _current_model = get_model_by_name(env_model)
            logger.info(f"Model from environment: {_current_model.display_name}")
            return _current_model
        except ValueError as e:
            logger.warning(f"Invalid MODEL_NAME env var: {e}")
    
    # Default
    _current_model = Models.gemini_flash()
    return _current_model


def get_model_name() -> str:
    """Get current model name."""
    return get_model_config().model_name


def get_provider() -> ModelProvider:
    """Get current provider."""
    return get_model_config().provider


# =============================================================================
# Convenience Functions for Cost Tracking
# =============================================================================

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for current model."""
    return get_model_config().estimate_cost(input_tokens, output_tokens)


def get_cost_per_1k_tokens() -> tuple:
    """Get (input_cost, output_cost) per 1K tokens."""
    config = get_model_config()
    return (config.input_cost_per_1k, config.output_cost_per_1k)
```

### 2. Provider-Specific API Clients

**File:** `literature_review/utils/llm_client.py`

```python
"""
Unified LLM Client Interface

Provides a consistent interface for making LLM calls regardless of provider.
Abstracts away provider-specific API differences.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod

from literature_review.config.model_config import (
    ModelConfig, ModelProvider, get_model_config
)

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def get_token_counts(self) -> Dict[str, int]:
        """Get token counts from last call."""
        pass


class GeminiClient(LLMClient):
    """Client for Google Gemini models."""
    
    def __init__(self, config: ModelConfig):
        from google import genai
        from google.genai import types
        
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {config.api_key_env}")
        
        self.client = genai.Client(api_key=api_key)
        self._last_usage = {"input": 0, "output": 0}
        
        # Configure generation settings
        thinking_config = types.ThinkingConfig(thinking_budget=0)
        self.json_config = types.GenerateContentConfig(
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_tokens,
            response_mime_type="application/json",
            thinking_config=thinking_config
        )
        self.text_config = types.GenerateContentConfig(
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_tokens,
            thinking_config=thinking_config
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        config = self.json_config if json_mode else self.text_config
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.client.models.generate_content(
            model=self.config.model_name,
            contents=full_prompt,
            config=config
        )
        
        # Track usage
        if hasattr(response, 'usage_metadata'):
            self._last_usage = {
                "input": response.usage_metadata.prompt_token_count,
                "output": response.usage_metadata.candidates_token_count
            }
        
        return response.text
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class OpenAIClient(LLMClient):
    """Client for OpenAI models."""
    
    def __init__(self, config: ModelConfig):
        from openai import OpenAI
        
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {config.api_key_env}")
        
        self.client = OpenAI(api_key=api_key)
        self._last_usage = {"input": 0, "output": 0}
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response_format = None
        if json_mode:
            response_format = {"type": "json_object"}
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format=response_format
        )
        
        # Track usage
        if response.usage:
            self._last_usage = {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens
            }
        
        return response.choices[0].message.content
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class AnthropicClient(LLMClient):
    """Client for Anthropic Claude models."""
    
    def __init__(self, config: ModelConfig):
        from anthropic import Anthropic
        
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {config.api_key_env}")
        
        self.client = Anthropic(api_key=api_key)
        self._last_usage = {"input": 0, "output": 0}
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        # Claude doesn't have native JSON mode; add instruction
        if json_mode:
            prompt = f"{prompt}\n\nRespond with valid JSON only."
        
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Track usage
        self._last_usage = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
        
        return response.content[0].text
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class LocalClient(LLMClient):
    """Client for local models via Ollama."""
    
    def __init__(self, config: ModelConfig):
        import requests
        
        self.config = config
        self.base_url = os.environ.get(config.api_key_env, "http://localhost:11434")
        self._last_usage = {"input": 0, "output": 0}
        
        # Verify connection
        try:
            requests.get(f"{self.base_url}/api/version", timeout=2)
        except Exception as e:
            logger.warning(f"Ollama not available at {self.base_url}: {e}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        import requests
        
        if json_mode:
            prompt = f"{prompt}\n\nRespond with valid JSON only."
        
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": self.config.temperature
            }
        }
        
        if json_mode:
            payload["format"] = "json"
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Track usage (Ollama provides token counts)
        self._last_usage = {
            "input": result.get("prompt_eval_count", 0),
            "output": result.get("eval_count", 0)
        }
        
        return result["response"]
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


# =============================================================================
# Client Factory
# =============================================================================

def get_llm_client(config: Optional[ModelConfig] = None) -> LLMClient:
    """
    Get an LLM client for the given or current configuration.
    
    Args:
        config: Optional model configuration. If None, uses current global config.
    
    Returns:
        Appropriate LLMClient instance for the provider.
    """
    if config is None:
        config = get_model_config()
    
    client_map = {
        ModelProvider.GEMINI: GeminiClient,
        ModelProvider.OPENAI: OpenAIClient,
        ModelProvider.ANTHROPIC: AnthropicClient,
        ModelProvider.LOCAL: LocalClient,
    }
    
    client_class = client_map.get(config.provider)
    if not client_class:
        raise ValueError(f"Unsupported provider: {config.provider}")
    
    return client_class(config)
```

### 3. Model Comparison Benchmark Tests

**File:** `tests/benchmarks/model_comparison/test_model_comparison.py`

```python
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

import pytest
import time
from typing import List, Dict, Any
from dataclasses import dataclass

from literature_review.config.model_config import (
    get_model_by_name,
    ModelConfig,
    get_available_models
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
                import json
                try:
                    data = json.loads(response)
                    accuracy = 0.0
                    if data.get("title"):
                        accuracy += 0.33
                    if data.get("authors") and len(data["authors"]) == 2:
                        accuracy += 0.33
                    if data.get("year") == 2024:
                        accuracy += 0.34
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


def pytest_addoption(parser):
    """Add model comparison options."""
    parser.addoption(
        "--models",
        action="store",
        default=None,
        help="Comma-separated list of models to compare"
    )
```

### 4. CLI Integration

**Updates to:** `pipeline_orchestrator.py`

```python
# Add to argument parser (after line 1040)
parser.add_argument(
    "--model",
    type=str,
    default=None,
    help="LLM model to use (e.g., gemini-2.5-flash, gpt-4-turbo, claude-sonnet). "
         "Can also be set via MODEL_NAME environment variable."
)

# Add to main() before pipeline execution (after argument parsing)
if args.model:
    from literature_review.config.model_config import set_model
    set_model(args.model)
    logger.info(f"Using model: {args.model}")
```

---

## Migration Guide

### Files Requiring Updates

The following files have hardcoded `model="gemini-2.5-flash"` that should be updated:

| File | Line | Change |
|------|------|--------|
| `literature_review/utils/api_manager.py` | 130, 149, 191 | Use `get_model_config().model_name` |
| `literature_review/reviewers/journal_reviewer.py` | 282 | Use `get_model_config().model_name` |
| `literature_review/reviewers/deep_reviewer.py` | 204 | Use `get_model_config().model_name` |
| `literature_review/orchestrator.py` | 412 | Use `get_model_config().model_name` |

### Example Migration

```python
# BEFORE
response = self.client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=current_config_object
)

# AFTER
from literature_review.config.model_config import get_model_config

model_config = get_model_config()
response = self.client.models.generate_content(
    model=model_config.model_name,
    contents=prompt,
    config=current_config_object
)
```

---

## Usage Examples

### Command-Line Usage

```bash
# Use default model (gemini-2.5-flash)
python pipeline_orchestrator.py --research-config research_config.json

# Use GPT-4 Turbo
python pipeline_orchestrator.py --model gpt-4-turbo

# Use Claude via environment variable
MODEL_NAME=claude-sonnet python pipeline_orchestrator.py

# Run model comparison benchmarks
pytest tests/benchmarks/model_comparison/ --models gemini-flash,gpt-4-turbo,claude-sonnet
```

### Programmatic Usage

```python
from literature_review.config.model_config import set_model, get_model_config

# Switch models programmatically
set_model("gpt-4-turbo")
config = get_model_config()
print(f"Using: {config.display_name}")
print(f"Cost: ${config.input_cost_per_1k}/1K input, ${config.output_cost_per_1k}/1K output")

# Use unified client interface
from literature_review.utils.llm_client import get_llm_client

client = get_llm_client()  # Uses current model
response = client.generate("Analyze this claim...", json_mode=True)
tokens = client.get_token_counts()
cost = config.estimate_cost(tokens["input"], tokens["output"])
```

---

## Dependencies

### Python Packages
- `google-genai>=0.3.0` - Gemini client (existing)
- `openai>=1.0.0` - OpenAI client (new, optional)
- `anthropic>=0.18.0` - Anthropic client (new, optional)
- `requests>=2.28.0` - For local Ollama (existing)

### Environment Variables
- `GEMINI_API_KEY` - Required for Gemini models
- `OPENAI_API_KEY` - Required for OpenAI models
- `ANTHROPIC_API_KEY` - Required for Anthropic models
- `OLLAMA_HOST` - Optional, defaults to localhost:11434
- `MODEL_NAME` - Optional, overrides default model

---

## Acceptance Criteria

- [ ] `ModelConfig` dataclass supports all major providers
- [ ] `get_model_config()` returns correct configuration
- [ ] `--model` CLI flag works in pipeline_orchestrator.py
- [ ] `MODEL_NAME` environment variable works
- [ ] MC-01: Same-prompt comparison test passes
- [ ] MC-02: Cost tracking works across providers
- [ ] MC-03: Latency measurement works
- [ ] Migration guide documents all required changes
- [ ] Existing tests pass with default model

---

## Implementation Notes

### Phase 1: Abstraction (8 hours)
- Create `model_config.py` with ModelConfig dataclass
- Create `llm_client.py` with provider abstraction
- Add `--model` CLI flag
- Update API manager to use abstraction

### Phase 2: Migration (4 hours)
- Update all hardcoded model references
- Add provider-specific error handling
- Add fallback behavior if provider unavailable
- Test with existing Gemini setup

### Future Enhancements
- Add model performance caching
- Implement automatic fallback between providers
- Add model-specific prompt optimization
- Support fine-tuned models
