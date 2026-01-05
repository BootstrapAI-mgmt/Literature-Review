"""
Unified LLM Client Interface

Provides a consistent interface for making LLM calls regardless of provider.
Abstracts away provider-specific API differences.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
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
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai package not installed. Install with: pip install google-genai"
            )
        
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
                "input": getattr(response.usage_metadata, 'prompt_token_count', 0),
                "output": getattr(response.usage_metadata, 'candidates_token_count', 0)
            }
        
        return response.text
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class OpenAIClient(LLMClient):
    """Client for OpenAI models."""
    
    def __init__(self, config: ModelConfig):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )
        
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
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )
        
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
