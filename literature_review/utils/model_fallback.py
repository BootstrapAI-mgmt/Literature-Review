"""
Model Fallback Chain Handler

Implements automatic fallback between models when quota errors or
failures occur, with configurable fallback chains.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass, field

from literature_review.config.model_config import (
    ModelConfig, get_model_by_name, get_model_config
)
from literature_review.utils.llm_client import get_llm_client

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
    errors: List[str] = field(default_factory=list)


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
