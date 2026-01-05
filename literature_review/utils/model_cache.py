"""
Model Response Cache Integration

Integrates the model abstraction layer with the existing API cache
for response caching across model switches.
"""

import hashlib
import json
import logging
import time
from typing import Optional
from pathlib import Path

from literature_review.config.model_config import ModelConfig, get_model_config

logger = logging.getLogger(__name__)


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
