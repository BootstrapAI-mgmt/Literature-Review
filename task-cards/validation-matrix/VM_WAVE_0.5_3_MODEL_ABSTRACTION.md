# Task Card: Model Abstraction Layer

**Task ID:** VM-W0.5-3  
**Wave:** 0.5 (Modularization Infrastructure)  
**Priority:** HIGH (P3 - Highest effort, enables LLM comparison)  
**Estimated Effort:** 14 hours *(+2h for rate limiting, fallback, and cache integration)*  
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
- [ ] Rate limiting works per-provider
- [ ] Fallback chain executes on quota errors
- [ ] Response caching integrates with existing API cache

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
    - Rate limiting configuration
    - Fallback chain support
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
    
    # Rate limiting configuration
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    retry_delay_seconds: float = 1.0
    max_retries: int = 3
    
    # Fallback configuration
    fallback_model: Optional[str] = None  # Model name to fall back to
    
    # Cache integration
    cache_responses: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour default
    
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
- [ ] Rate limiter respects per-provider limits
- [ ] Fallback chain handles quota errors gracefully
- [ ] Response cache integrates with existing infrastructure
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

---

## Additional Deliverables

### Rate Limiting Manager

**File:** `literature_review/utils/rate_limiter.py`

```python
"""
Per-Provider Rate Limiting

Implements token bucket rate limiting for each LLM provider to prevent
quota errors and enable graceful degradation.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional
from collections import deque

from literature_review.config.model_config import ModelConfig, ModelProvider


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def acquire(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """Acquire tokens, blocking until available or timeout."""
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            with self.lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Wait before retry
            time.sleep(0.1)
        
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    """Manages rate limiting across all providers."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._buckets = {}
        return cls._instance
    
    def get_bucket(self, config: ModelConfig) -> RateLimitBucket:
        """Get or create rate limit bucket for a model config."""
        key = f"{config.provider.value}:{config.model_name}"
        
        if key not in self._buckets:
            self._buckets[key] = RateLimitBucket(
                capacity=config.requests_per_minute,
                refill_rate=config.requests_per_minute / 60.0
            )
        
        return self._buckets[key]
    
    def acquire(self, config: ModelConfig, tokens: int = 1) -> bool:
        """Acquire rate limit tokens for the given model."""
        bucket = self.get_bucket(config)
        return bucket.acquire(tokens)
    
    def wait_for_capacity(self, config: ModelConfig):
        """Wait until rate limit capacity is available."""
        bucket = self.get_bucket(config)
        bucket.acquire(1, timeout=60.0)


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return RateLimiter()
```

### Fallback Chain Handler

**File:** `literature_review/utils/model_fallback.py`

```python
"""
Model Fallback Chain Handler

Implements automatic fallback between models when quota errors or
failures occur, with configurable fallback chains.
"""

import logging
from typing import List, Optional, Callable, Any
from dataclasses import dataclass

from literature_review.config.model_config import (
    ModelConfig, get_model_by_name, get_model_config
)
from literature_review.utils.llm_client import get_llm_client, LLMClient

logger = logging.getLogger(__name__)


# Default fallback chains per provider
DEFAULT_FALLBACK_CHAINS = {
    "gemini-2.5-flash": ["gemini-1.5-pro", "gpt-4-turbo"],
    "gpt-4-turbo": ["gpt-4o", "gemini-2.5-flash"],
    "gpt-4o": ["gpt-4-turbo", "gemini-2.5-flash"],
    "claude-3.5-sonnet": ["claude-3-opus", "gpt-4-turbo"],
}


@dataclass
class FallbackResult:
    """Result from a fallback chain execution."""
    success: bool
    model_used: str
    response: Optional[str] = None
    attempts: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ModelFallbackHandler:
    """Handles automatic fallback between models."""
    
    def __init__(self, primary_model: Optional[str] = None):
        self.primary_model = primary_model or get_model_config().model_name
        self.fallback_chains = DEFAULT_FALLBACK_CHAINS.copy()
    
    def set_fallback_chain(self, model: str, fallbacks: List[str]):
        """Set custom fallback chain for a model."""
        self.fallback_chains[model] = fallbacks
    
    def get_fallback_chain(self, model: str) -> List[str]:
        """Get fallback chain for a model."""
        chain = [model]
        
        # Add configured fallbacks
        if model in self.fallback_chains:
            chain.extend(self.fallback_chains[model])
        
        # Also check model config for single fallback
        try:
            config = get_model_by_name(model)
            if config.fallback_model and config.fallback_model not in chain:
                chain.append(config.fallback_model)
        except ValueError:
            pass
        
        return chain
    
    def execute_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        max_attempts: int = 3
    ) -> FallbackResult:
        """
        Execute a prompt with automatic fallback.
        
        Tries the primary model first, then falls back through the chain
        if quota or rate limit errors occur.
        """
        chain = self.get_fallback_chain(self.primary_model)
        errors = []
        
        for i, model_name in enumerate(chain[:max_attempts]):
            try:
                config = get_model_by_name(model_name)
                client = get_llm_client(config)
                
                response = client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    json_mode=json_mode
                )
                
                return FallbackResult(
                    success=True,
                    model_used=model_name,
                    response=response,
                    attempts=i + 1,
                    errors=errors
                )
                
            except Exception as e:
                error_msg = f"{model_name}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Model {model_name} failed: {e}")
                
                # Check if it's a recoverable error
                if not self._is_recoverable_error(e):
                    break
        
        return FallbackResult(
            success=False,
            model_used=chain[0],
            attempts=len(errors),
            errors=errors
        )
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Check if error is recoverable via fallback."""
        error_str = str(error).lower()
        recoverable_patterns = [
            "rate limit",
            "quota exceeded",
            "429",
            "503",
            "temporarily unavailable",
            "overloaded"
        ]
        return any(p in error_str for p in recoverable_patterns)


def execute_with_fallback(
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    primary_model: Optional[str] = None
) -> FallbackResult:
    """Convenience function for fallback execution."""
    handler = ModelFallbackHandler(primary_model)
    return handler.execute_with_fallback(prompt, system_prompt, json_mode)
```

### Cache Integration

**File:** `literature_review/utils/model_cache.py`

```python
"""
Model Response Cache Integration

Integrates the model abstraction layer with the existing API cache
for response caching across model switches.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from literature_review.config.model_config import ModelConfig, get_model_config

logger = logging.getLogger(__name__)

# Try to import existing cache infrastructure
try:
    from literature_review.utils.api_manager import get_cache_path, load_cache, save_cache
    HAS_API_CACHE = True
except ImportError:
    HAS_API_CACHE = False


class ModelResponseCache:
    """Cache for model responses with model-aware keying."""
    
    def __init__(self, cache_dir: str = "api_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _make_key(self, prompt: str, config: ModelConfig) -> str:
        """Create cache key from prompt and model config."""
        key_data = {
            "prompt": prompt,
            "model": config.model_name,
            "provider": config.provider.value,
            "temperature": config.temperature,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def get(self, prompt: str, config: Optional[ModelConfig] = None) -> Optional[str]:
        """Get cached response if available."""
        if config is None:
            config = get_model_config()
        
        if not config.cache_responses:
            return None
        
        key = self._make_key(prompt, config)
        cache_file = self.cache_dir / f"model_{key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                
                # Check TTL
                import time
                if time.time() - data.get("timestamp", 0) < config.cache_ttl_seconds:
                    logger.debug(f"Cache hit for {config.model_name}: {key}")
                    return data.get("response")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        return None
    
    def set(self, prompt: str, response: str, config: Optional[ModelConfig] = None):
        """Cache a response."""
        if config is None:
            config = get_model_config()
        
        if not config.cache_responses:
            return
        
        key = self._make_key(prompt, config)
        cache_file = self.cache_dir / f"model_{key}.json"
        
        import time
        data = {
            "prompt": prompt[:200],  # Truncated for reference
            "response": response,
            "model": config.model_name,
            "timestamp": time.time()
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Cached response for {config.model_name}: {key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")


# Global cache instance
_model_cache: Optional[ModelResponseCache] = None


def get_model_cache() -> ModelResponseCache:
    """Get global model cache instance."""
    global _model_cache
    if _model_cache is None:
        _model_cache = ModelResponseCache()
    return _model_cache
```

---

## Cross-Task Integration

This task integrates with the other Wave 0.5 tasks:

### Integration with VM-W0.5-1 (Metrics Configuration)

Model-specific metrics can be tracked in the metrics config:

```yaml
# tests/validation/config/metrics.yaml

metrics:
  # Model-specific latency thresholds
  - id: MC-03-GEMINI
    name: Gemini Latency Baseline
    category: benchmark
    threshold: 2.0
    unit: seconds
    
  - id: MC-03-GPT4
    name: GPT-4 Latency Baseline
    category: benchmark
    threshold: 5.0
    unit: seconds
    
  - id: MC-03-CLAUDE
    name: Claude Latency Baseline
    category: benchmark
    threshold: 4.0
    unit: seconds
```

### Integration with VM-W0.5-2 (Domain Fixtures)

Domain-model matrix testing for comprehensive validation:

```python
# tests/validation/test_domain_model_matrix.py

import pytest
from itertools import product

DOMAINS = ["neuromorphic-computing", "thermophoresis"]
MODELS = ["gemini-flash", "gpt-4-turbo"]

@pytest.mark.parametrize("domain,model", list(product(DOMAINS, MODELS)))
def test_domain_model_combination(domain, model):
    """Test all domain × model combinations."""
    from tests.validation.fixtures.domain_fixture import get_domain_fixture
    from literature_review.config.model_config import set_model
    
    fixture = get_domain_fixture(domain)
    model_config = set_model(model)
    
    # Run validation with specific domain and model
    results = run_claim_validation(
        claims=fixture.golden_dataset.claims[:10],
        model_config=model_config
    )
    
    assert results.accuracy >= fixture.baselines.judge_accuracy
```

### Combined Validation Context Fixture

```python
# tests/conftest.py - Combined fixture for all Wave 0.5 features

@pytest.fixture
def validation_context(metrics_config, domain_fixture, request):
    """Combined validation context with all modularization features."""
    from literature_review.config.model_config import get_model_config, set_model
    
    model_name = request.config.getoption("--model", default=None)
    if model_name:
        set_model(model_name)
    
    return {
        "metrics": metrics_config,
        "domain": domain_fixture,
        "model": get_model_config(),
        "profile": metrics_config.active_profile,
    }


@pytest.fixture
def full_validation_context(validation_context, request):
    """Full context with rate limiting and fallback enabled."""
    from literature_review.utils.rate_limiter import get_rate_limiter
    from literature_review.utils.model_fallback import ModelFallbackHandler
    
    return {
        **validation_context,
        "rate_limiter": get_rate_limiter(),
        "fallback_handler": ModelFallbackHandler(
            validation_context["model"].model_name
        ),
    }
```
