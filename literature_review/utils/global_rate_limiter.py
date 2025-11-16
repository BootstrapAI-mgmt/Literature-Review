"""
Global API Rate Limiter and Error Categorization System
Version: 1.0
Date: 2025-11-15

This module provides:
1. Global rate limiting across all pipeline modules
2. Intelligent error categorization
3. Error-specific handling strategies
4. Request validation to prevent wasted API calls
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum
import threading
import json
import os

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categorization of API errors for intelligent handling"""
    # Service-level errors (Google's side)
    SERVICE_OVERLOADED = "service_overloaded"  # 503 - retry after delay
    SERVICE_UNAVAILABLE = "service_unavailable"  # 503 - retry after delay
    RATE_LIMIT = "rate_limit"  # 429 - wait for quota reset
    
    # Client-level errors (our side)
    INVALID_REQUEST = "invalid_request"  # 400 - fix and retry
    AUTHENTICATION = "authentication"  # 401/403 - check API key
    CONTENT_POLICY = "content_policy"  # 400 - skip document
    MALFORMED_RESPONSE = "malformed_response"  # Parse error - retry once
    
    # Document-level errors
    EMPTY_INPUT = "empty_input"  # No content to process
    INVALID_FORMAT = "invalid_format"  # Bad document format
    TOO_LARGE = "too_large"  # Document exceeds limits
    
    # Unknown/Other
    UNKNOWN = "unknown"


class ErrorAction(Enum):
    """Actions to take based on error category"""
    RETRY_IMMEDIATE = "retry_immediate"  # Retry right away (1-2 attempts)
    RETRY_WITH_DELAY = "retry_with_delay"  # Wait then retry
    RETRY_LONG_DELAY = "retry_long_delay"  # Wait longer then retry
    SKIP_DOCUMENT = "skip_document"  # Mark document as failed, move on
    REQUEUE_DOCUMENT = "requeue_document"  # Put back in queue for later
    ABORT_PIPELINE = "abort_pipeline"  # Critical error, stop everything
    LOG_AND_CONTINUE = "log_and_continue"  # Log but continue


class GlobalRateLimiter:
    """
    Singleton class to track API usage across all pipeline modules.
    Prevents quota exhaustion by coordinating between modules.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.global_rpm_limit = 10  # Conservative global limit
        self.available_rpm = 1000  # What Google provides
        self.calls_this_minute = 0
        self.minute_start = time.time()
        self.total_calls = 0
        self.error_counts = {}
        self.last_errors = []  # Track recent errors
        self.max_error_history = 100
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        self.lock = threading.Lock()
        
        # Error categorization rules
        self.error_rules = self._build_error_rules()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "errors_by_category": {},
            "actions_taken": {},
            "quota_pauses": 0,
            "documents_skipped": 0,
            "documents_requeued": 0
        }
        
        self._initialized = True
        logger.info(f"[GLOBAL LIMITER] Initialized with {self.global_rpm_limit} RPM limit (max available: {self.available_rpm})")
    
    def _build_error_rules(self) -> Dict[ErrorCategory, ErrorAction]:
        """Define how to handle each error category"""
        return {
            # Service errors - wait and retry
            ErrorCategory.SERVICE_OVERLOADED: ErrorAction.RETRY_LONG_DELAY,
            ErrorCategory.SERVICE_UNAVAILABLE: ErrorAction.RETRY_LONG_DELAY,
            ErrorCategory.RATE_LIMIT: ErrorAction.RETRY_LONG_DELAY,
            
            # Client errors - fix or skip
            ErrorCategory.INVALID_REQUEST: ErrorAction.SKIP_DOCUMENT,
            ErrorCategory.AUTHENTICATION: ErrorAction.ABORT_PIPELINE,
            ErrorCategory.CONTENT_POLICY: ErrorAction.SKIP_DOCUMENT,
            ErrorCategory.MALFORMED_RESPONSE: ErrorAction.RETRY_IMMEDIATE,
            
            # Document errors - skip or requeue
            ErrorCategory.EMPTY_INPUT: ErrorAction.SKIP_DOCUMENT,
            ErrorCategory.INVALID_FORMAT: ErrorAction.SKIP_DOCUMENT,
            ErrorCategory.TOO_LARGE: ErrorAction.SKIP_DOCUMENT,
            
            # Unknown - be conservative
            ErrorCategory.UNKNOWN: ErrorAction.RETRY_WITH_DELAY
        }
    
    def categorize_error(self, error: Exception, response_text: str = "") -> ErrorCategory:
        """
        Categorize an error and return category.
        Returns: ErrorCategory
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Check for specific Google API errors
        if "503" in error_str or "unavailable" in error_str:
            if "overloaded" in error_str:
                return ErrorCategory.SERVICE_OVERLOADED
            return ErrorCategory.SERVICE_UNAVAILABLE
        
        if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
            return ErrorCategory.RATE_LIMIT
        
        if "400" in error_str:
            if "content" in error_str and "policy" in error_str:
                return ErrorCategory.CONTENT_POLICY
            return ErrorCategory.INVALID_REQUEST
        
        if "401" in error_str or "403" in error_str or "authentication" in error_str:
            return ErrorCategory.AUTHENTICATION
        
        # JSON/response errors
        if "jsondecode" in error_type.lower() or "json" in error_str:
            if len(response_text) < 10:
                return ErrorCategory.EMPTY_INPUT
            return ErrorCategory.MALFORMED_RESPONSE
        
        # Document-level errors
        if "empty" in error_str or len(response_text) == 0:
            return ErrorCategory.EMPTY_INPUT
        
        if "too large" in error_str or "token" in error_str:
            return ErrorCategory.TOO_LARGE
        
        return ErrorCategory.UNKNOWN
    
    def get_action_for_error(self, category: ErrorCategory, attempt: int = 1) -> ErrorAction:
        """
        Get recommended action for error category.
        Returns: ErrorAction
        """
        return self.error_rules.get(category, ErrorAction.LOG_AND_CONTINUE)
    
    def should_abort_pipeline(self) -> bool:
        """Check if we should abort the entire pipeline due to error patterns"""
        # Abort if too many consecutive errors
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.critical(f"[ABORT] {self.consecutive_errors} consecutive errors. Aborting pipeline.")
            return True
        
        # Abort if error rate is extremely high (>90% of last 20 calls)
        if len(self.last_errors) >= 20:
            recent_error_rate = sum(1 for e in self.last_errors[-20:] if e) / 20
            if recent_error_rate > 0.9:
                logger.critical(f"[ABORT] Error rate {recent_error_rate:.1%} in last 20 calls. Aborting.")
                return True
        
        return False
    
    def validate_request(self, prompt: str, config: dict = None) -> Tuple[bool, str]:
        """
        Validate request before making API call to prevent wasted requests.
        Returns: (is_valid, reason_if_invalid)
        """
        # Check if prompt is empty or too short
        if not prompt or len(prompt.strip()) < 10:
            return False, "Prompt is empty or too short (< 10 chars)"
        
        # Check if prompt is suspiciously short for a complex task
        if config and config.get("response_mime_type") == "application/json":
            if len(prompt) < 100:
                logger.warning(f"[VALIDATION] Suspiciously short prompt for JSON response: {len(prompt)} chars")
        
        # Check for common malformed prompts
        if prompt.count("{") != prompt.count("}"):
            return False, "Malformed prompt: mismatched braces"
        
        # Check if we've seen this exact error pattern recently
        if len(self.last_errors) >= 3:
            recent_errors = [e for e in self.last_errors[-3:] if e]
            if len(recent_errors) == 3 and all(e[0] == recent_errors[0][0] for e in recent_errors):
                return False, f"Same error repeating: {recent_errors[0][1]}"
        
        return True, ""
    
    def wait_for_quota(self) -> None:
        """Global rate limiting across all modules"""
        with self.lock:
            current_time = time.time()
            
            # Reset counter every 60 seconds
            if current_time - self.minute_start >= 60:
                self.calls_this_minute = 0
                self.minute_start = current_time
            
            # Check if we need to wait
            if self.calls_this_minute >= self.global_rpm_limit:
                sleep_time = 60.1 - (current_time - self.minute_start)
                if sleep_time > 0:
                    self.stats["quota_pauses"] += 1
                    logger.info(f"[GLOBAL LIMITER] Rate limit ({self.global_rpm_limit}/min) reached. Sleeping {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    self.calls_this_minute = 0
                    self.minute_start = time.time()
            
            self.calls_this_minute += 1
            self.total_calls += 1
    
    def record_request(self, success: bool, error: Optional[Exception] = None, response_text: str = "") -> None:
        """Record API request outcome for statistics and error tracking"""
        with self.lock:
            self.stats["total_requests"] += 1
            
            if success:
                self.stats["successful_requests"] += 1
                self.consecutive_errors = 0
                self.last_errors.append(None)
            else:
                self.stats["failed_requests"] += 1
                self.consecutive_errors += 1
                
                if error:
                    category = self.categorize_error(error, response_text)
                    reason = str(error)  # Extract reason from error message
                    
                    # Update statistics
                    cat_name = category.value
                    self.stats["errors_by_category"][cat_name] = self.stats["errors_by_category"].get(cat_name, 0) + 1
                    self.error_counts[cat_name] = self.error_counts.get(cat_name, 0) + 1
                    
                    # Track error
                    self.last_errors.append((category, reason, datetime.now()))
                    
                    # Log details
                    logger.error(f"[ERROR TRACKING] Category: {cat_name}, Reason: {reason}")
            
            # Trim error history
            if len(self.last_errors) > self.max_error_history:
                self.last_errors = self.last_errors[-self.max_error_history:]
    
    def record_action(self, action: ErrorAction, document: str = None) -> None:
        """Record action taken in response to error"""
        with self.lock:
            action_name = action.value
            self.stats["actions_taken"][action_name] = self.stats["actions_taken"].get(action_name, 0) + 1
            
            if action == ErrorAction.SKIP_DOCUMENT:
                self.stats["documents_skipped"] += 1
                if document:
                    logger.warning(f"[SKIPPED] Document: {document}")
            elif action == ErrorAction.REQUEUE_DOCUMENT:
                self.stats["documents_requeued"] += 1
                if document:
                    logger.info(f"[REQUEUED] Document: {document}")
    
    def get_statistics(self) -> Dict:
        """Get current statistics"""
        with self.lock:
            stats = self.stats.copy()
            if stats["total_requests"] > 0:
                stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
                stats["error_rate"] = stats["failed_requests"] / stats["total_requests"]
            else:
                stats["success_rate"] = 0.0
                stats["error_rate"] = 0.0
            
            stats["calls_this_minute"] = self.calls_this_minute
            stats["total_calls"] = self.total_calls
            stats["consecutive_errors"] = self.consecutive_errors
            
            return stats
    
    def print_statistics(self) -> None:
        """Print formatted statistics"""
        stats = self.get_statistics()
        
        print("\n" + "=" * 80)
        print("GLOBAL API STATISTICS")
        print("=" * 80)
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Successful: {stats['successful_requests']} ({stats['success_rate']:.1%})")
        print(f"Failed: {stats['failed_requests']} ({stats['error_rate']:.1%})")
        print(f"Consecutive Errors: {stats['consecutive_errors']}")
        print(f"Quota Pauses: {stats['quota_pauses']}")
        
        if stats.get("errors_by_category"):
            print("\nErrors by Category:")
            for category, count in sorted(stats["errors_by_category"].items(), key=lambda x: -x[1]):
                print(f"  {category}: {count}")
        
        if stats.get("actions_taken"):
            print("\nActions Taken:")
            for action, count in sorted(stats["actions_taken"].items(), key=lambda x: -x[1]):
                print(f"  {action}: {count}")
        
        print(f"\nDocuments Skipped: {stats['documents_skipped']}")
        print(f"Documents Requeued: {stats['documents_requeued']}")
        print("=" * 80 + "\n")
    
    def reset_statistics(self) -> None:
        """Reset all statistics"""
        with self.lock:
            self.stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "errors_by_category": {},
                "actions_taken": {},
                "quota_pauses": 0,
                "documents_skipped": 0,
                "documents_requeued": 0
            }
            self.consecutive_errors = 0
            self.last_errors = []
            logger.info("[GLOBAL LIMITER] Statistics reset")


# Singleton instance
global_limiter = GlobalRateLimiter()
