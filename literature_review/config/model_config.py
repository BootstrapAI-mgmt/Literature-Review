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
from typing import Optional, Dict, Callable
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
            logger.warning(
                "API key is not set for model '%s' (provider: %s)",
                self.model_name,
                self.provider.value,
            )
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
            max_context_length=1000000,
            requests_per_minute=10,  # Conservative limit
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
            max_context_length=2000000,
            requests_per_minute=10,
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


def reset_model_config() -> None:
    """Reset the model configuration to default (useful for testing)."""
    global _current_model
    _current_model = None


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
