"""
Unit tests for RetryPolicy class.

Tests cover:
- Exponential backoff calculation
- Error classification (retryable vs permanent)
- Circuit breaker behavior
- Max attempts enforcement
- Stage-specific configuration
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline_orchestrator import RetryPolicy


class TestRetryPolicy:
    """Test suite for RetryPolicy class."""
    
    def test_exponential_backoff_basic(self):
        """Test exponential backoff calculation."""
        config = {
            'retry_policy': {
                'default_backoff_base': 2,
                'default_backoff_max': 60
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 1: 2^0 = 1s (+ jitter)
        delay1 = policy.calculate_backoff(1, 'test_stage')
        assert 0.8 <= delay1 <= 1.2, f"Delay 1 out of range: {delay1}"
        
        # Attempt 2: 2^1 = 2s (+ jitter)
        delay2 = policy.calculate_backoff(2, 'test_stage')
        assert 1.6 <= delay2 <= 2.4, f"Delay 2 out of range: {delay2}"
        
        # Attempt 3: 2^2 = 4s (+ jitter)
        delay3 = policy.calculate_backoff(3, 'test_stage')
        assert 3.2 <= delay3 <= 4.8, f"Delay 3 out of range: {delay3}"
    
    def test_exponential_backoff_max_cap(self):
        """Test that backoff is capped at max_delay."""
        config = {
            'retry_policy': {
                'default_backoff_base': 2,
                'default_backoff_max': 60
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 10: 2^9 = 512s, but capped at 60s (+ jitter)
        delay10 = policy.calculate_backoff(10, 'test_stage')
        assert delay10 <= 60 * 1.2, f"Delay 10 not capped: {delay10}"
        assert delay10 >= 48, f"Delay 10 too low: {delay10}"  # 60 - 20% jitter
    
    def test_exponential_backoff_different_base(self):
        """Test backoff with different base values."""
        config = {
            'retry_policy': {
                'default_backoff_base': 1.5,
                'default_backoff_max': 100
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 1: 1.5^0 = 1s
        delay1 = policy.calculate_backoff(1, 'test_stage')
        assert 0.8 <= delay1 <= 1.2
        
        # Attempt 2: 1.5^1 = 1.5s
        delay2 = policy.calculate_backoff(2, 'test_stage')
        assert 1.2 <= delay2 <= 1.8
        
        # Attempt 3: 1.5^2 = 2.25s
        delay3 = policy.calculate_backoff(3, 'test_stage')
        assert 1.8 <= delay3 <= 2.7
    
    def test_error_classification_retryable(self):
        """Test that retryable errors are identified."""
        policy = RetryPolicy({'retry_policy': {'enabled': True}})
        
        # Retryable errors
        assert policy.is_retryable_error("Connection timeout", "test")[0] == True
        assert policy.is_retryable_error("Rate limit exceeded", "test")[0] == True
        assert policy.is_retryable_error("Network error occurred", "test")[0] == True
        assert policy.is_retryable_error("HTTP 503 Service Unavailable", "test")[0] == True
        assert policy.is_retryable_error("Connection refused", "test")[0] == True
        assert policy.is_retryable_error("Too many requests (429)", "test")[0] == True
        assert policy.is_retryable_error("Temporary failure", "test")[0] == True
        assert policy.is_retryable_error("Network unreachable", "test")[0] == True
    
    def test_error_classification_permanent(self):
        """Test that permanent errors are not retried."""
        policy = RetryPolicy({'retry_policy': {'enabled': True}})
        
        # Permanent errors
        assert policy.is_retryable_error("SyntaxError: invalid syntax", "test")[0] == False
        assert policy.is_retryable_error("FileNotFoundError: file.json", "test")[0] == False
        assert policy.is_retryable_error("NameError: 'x' is not defined", "test")[0] == False
        assert policy.is_retryable_error("HTTP 401 Unauthorized", "test")[0] == False
        assert policy.is_retryable_error("HTTP 403 Forbidden", "test")[0] == False
        assert policy.is_retryable_error("TypeError: unsupported type", "test")[0] == False
        assert policy.is_retryable_error("AttributeError: no attribute", "test")[0] == False
        assert policy.is_retryable_error("ImportError: no module", "test")[0] == False
        assert policy.is_retryable_error("Permission denied", "test")[0] == False
    
    def test_error_classification_custom_patterns(self):
        """Test custom retryable patterns."""
        config = {
            'retry_policy': {
                'enabled': True,
                'per_stage': {
                    'custom_stage': {
                        'retryable_patterns': ['quota exceeded', 'throttled']
                    }
                }
            }
        }
        policy = RetryPolicy(config)
        
        # Custom patterns should be retryable
        assert policy.is_retryable_error("API quota exceeded", "custom_stage")[0] == True
        assert policy.is_retryable_error("Request throttled", "custom_stage")[0] == True
        
        # Standard patterns should still work
        assert policy.is_retryable_error("Connection timeout", "custom_stage")[0] == True
    
    def test_circuit_breaker(self):
        """Test circuit breaker stops retries after threshold."""
        config = {
            'retry_policy': {
                'enabled': True,
                'circuit_breaker_threshold': 3
            }
        }
        policy = RetryPolicy(config)
        
        # First 3 failures
        policy.record_failure()
        policy.record_failure()
        policy.record_failure()
        
        # Should not retry after circuit breaker trips
        is_retryable, reason = policy.is_retryable_error("Connection timeout", "test")
        assert is_retryable == False
        assert "circuit breaker" in reason.lower()
    
    def test_circuit_breaker_reset(self):
        """Test circuit breaker resets on success."""
        config = {
            'retry_policy': {
                'enabled': True,
                'circuit_breaker_threshold': 3
            }
        }
        policy = RetryPolicy(config)
        
        # Record some failures
        policy.record_failure()
        policy.record_failure()
        
        # Record success - should reset
        policy.record_success()
        
        # Should be able to retry again
        is_retryable, reason = policy.is_retryable_error("Connection timeout", "test")
        assert is_retryable == True
    
    def test_max_attempts_exceeded(self):
        """Test that max attempts limit is enforced."""
        config = {
            'retry_policy': {
                'default_max_attempts': 3
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 3 (max is 3)
        should_retry, reason, delay = policy.should_retry(3, 'test', 'timeout')
        assert should_retry == False
        assert "max attempts" in reason.lower()
    
    def test_should_retry_within_limit(self):
        """Test should_retry returns True within attempt limit."""
        config = {
            'retry_policy': {
                'default_max_attempts': 5
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 2 (max is 5)
        should_retry, reason, delay = policy.should_retry(2, 'test', 'Connection timeout')
        assert should_retry == True
        assert "retrying" in reason.lower()
        assert delay > 0
    
    def test_should_retry_permanent_error(self):
        """Test should_retry returns False for permanent errors."""
        config = {
            'retry_policy': {
                'default_max_attempts': 5
            }
        }
        policy = RetryPolicy(config)
        
        # Permanent error should not retry
        should_retry, reason, delay = policy.should_retry(1, 'test', 'SyntaxError: invalid')
        assert should_retry == False
        assert "permanent error" in reason.lower()
        assert delay == 0
    
    def test_retry_disabled(self):
        """Test that retry is disabled when configured."""
        config = {
            'retry_policy': {
                'enabled': False
            }
        }
        policy = RetryPolicy(config)
        
        # Should not retry even for retryable errors
        is_retryable, reason = policy.is_retryable_error("Connection timeout", "test")
        assert is_retryable == False
        assert "retry disabled" in reason.lower()
    
    def test_stage_specific_config(self):
        """Test that stage-specific config overrides defaults."""
        config = {
            'retry_policy': {
                'default_max_attempts': 3,
                'default_backoff_base': 2,
                'per_stage': {
                    'special_stage': {
                        'max_attempts': 5,
                        'backoff_base': 1.5,
                        'backoff_max': 30
                    }
                }
            }
        }
        policy = RetryPolicy(config)
        
        # Default stage uses default config
        default_config = policy.get_stage_config('normal_stage')
        assert default_config['max_attempts'] == 3
        assert default_config['backoff_base'] == 2
        
        # Special stage uses custom config
        special_config = policy.get_stage_config('special_stage')
        assert special_config['max_attempts'] == 5
        assert special_config['backoff_base'] == 1.5
        assert special_config['backoff_max'] == 30
    
    def test_unknown_error_conservative(self):
        """Test that unknown errors are not retried (conservative)."""
        policy = RetryPolicy({'retry_policy': {'enabled': True}})
        
        # Unknown error should not be retried
        is_retryable, reason = policy.is_retryable_error("Some random error message", "test")
        assert is_retryable == False
        assert "unknown error" in reason.lower() or "conservative" in reason.lower()
    
    def test_case_insensitive_matching(self):
        """Test that error matching is case-insensitive."""
        policy = RetryPolicy({'retry_policy': {'enabled': True}})
        
        # Various case combinations
        assert policy.is_retryable_error("CONNECTION TIMEOUT", "test")[0] == True
        assert policy.is_retryable_error("Connection Timeout", "test")[0] == True
        assert policy.is_retryable_error("connection timeout", "test")[0] == True
        assert policy.is_retryable_error("RATE LIMIT EXCEEDED", "test")[0] == True
    
    @pytest.mark.unit
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to backoff."""
        config = {
            'retry_policy': {
                'default_backoff_base': 2,
                'default_backoff_max': 60
            }
        }
        policy = RetryPolicy(config)
        
        # Calculate multiple delays for same attempt
        delays = [policy.calculate_backoff(3, 'test_stage') for _ in range(10)]
        
        # All delays should be in expected range
        for delay in delays:
            assert 3.2 <= delay <= 4.8
        
        # Not all delays should be identical (randomness)
        assert len(set(delays)) > 1, "Jitter should add randomness"
    
    @pytest.mark.unit
    def test_minimum_delay(self):
        """Test that minimum delay is 1 second."""
        config = {
            'retry_policy': {
                'default_backoff_base': 0.5,  # Very small base
                'default_backoff_max': 60
            }
        }
        policy = RetryPolicy(config)
        
        # Even with small base, delay should be at least 1 second
        delay = policy.calculate_backoff(1, 'test_stage')
        assert delay >= 1.0
