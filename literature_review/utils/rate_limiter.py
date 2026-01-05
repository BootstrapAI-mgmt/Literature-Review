"""
Per-Provider Rate Limiting

Implements token bucket rate limiting for each LLM provider to prevent
quota errors and enable graceful degradation.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict

from literature_review.config.model_config import ModelConfig


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def __post_init__(self):
        # Initialize with full capacity
        self.tokens = float(self.capacity)
    
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
                    cls._instance._init_buckets()
        return cls._instance
    
    def _init_buckets(self):
        """Initialize buckets dictionary. Called only once during singleton creation."""
        self._buckets: Dict[str, RateLimitBucket] = {}
        self._bucket_lock = threading.Lock()
    
    def get_bucket(self, config: ModelConfig) -> RateLimitBucket:
        """Get or create rate limit bucket for a model config."""
        key = f"{config.provider.value}:{config.model_name}"
        
        with self._bucket_lock:
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
    
    def reset(self):
        """Reset all rate limit buckets (useful for testing)."""
        with self._bucket_lock:
            self._buckets = {}


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return RateLimiter()
