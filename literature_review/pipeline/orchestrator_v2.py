"""
Pipeline Orchestrator v2.0 - Advanced Pipeline Features

This module provides enhanced pipeline features:
- Parallel processing of multiple papers (configurable concurrency)
- Advanced quota management and throttling
- Dry-run mode for validation without side effects
- Enhanced checkpoint tracking for per-paper status
- Smart error classification and retry logic

Features are backward compatible with v1.x and can be enabled via feature flags.
"""

import os
import re
import json
import time
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from threading import Lock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from enum import Enum


class ErrorType(Enum):
    """Classification of error types for smart retry logic."""
    TRANSIENT = "transient"  # Retryable errors (timeouts, rate limits)
    PERMANENT = "permanent"  # Non-retryable errors (syntax errors, auth failures)
    UNKNOWN = "unknown"      # Unknown error type (conservative: no retry)


@dataclass
class PaperStatus:
    """Status of a single paper in the pipeline."""
    paper_id: str
    stage: str  # 'not_started', 'in_progress', 'completed', 'failed'
    stages_completed: List[str]
    retries: int
    last_error: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    stage_timestamps: Dict[str, str]  # stage_name -> timestamp


class ErrorClassifier:
    """Classifies errors as transient, permanent, or unknown for retry logic."""
    
    # Transient error patterns (retryable)
    TRANSIENT_PATTERNS = [
        r'timeout', r'timed? ?out', r'time ?out',
        r'connection refused', r'connection reset', r'connection error',
        r'rate ?limit', r'too many requests', r'429',
        r'temporary failure', r'transient',
        r'network error', r'network unreachable',
        r'service unavailable', r'503', r'502', r'504',
        r'gateway timeout', r'bad gateway',
        r'deadline exceeded', r'resource temporarily unavailable',
    ]
    
    # Permanent error patterns (non-retryable)
    PERMANENT_PATTERNS = [
        r'syntax error', r'name ?error', r'type ?error',
        r'file not found', r'no such file', r'invalid',
        r'parse error', r'attribute ?error', r'import ?error',
        r'permission denied', r'401', r'403',
        r'not found', r'404', r'bad request', r'400',
        r'unprocessable entity', r'422',
        r'method not allowed', r'405',
    ]
    
    @classmethod
    def classify_error(cls, error_message: str, http_status: Optional[int] = None) -> ErrorType:
        """
        Classify an error as transient, permanent, or unknown.
        
        Args:
            error_message: Error message or stderr output
            http_status: Optional HTTP status code
            
        Returns:
            ErrorType classification
        """
        error_lower = error_message.lower()
        
        # Check HTTP status codes first
        if http_status:
            if http_status in [408, 429, 502, 503, 504]:
                return ErrorType.TRANSIENT
            elif http_status in [400, 401, 403, 404, 405, 422]:
                return ErrorType.PERMANENT
        
        # Check transient patterns
        for pattern in cls.TRANSIENT_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return ErrorType.TRANSIENT
        
        # Check permanent patterns
        for pattern in cls.PERMANENT_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return ErrorType.PERMANENT
        
        # Unknown error type - conservative: don't retry
        return ErrorType.UNKNOWN
    
    @classmethod
    def should_retry(cls, error_message: str, http_status: Optional[int] = None) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error_message: Error message or stderr output
            http_status: Optional HTTP status code
            
        Returns:
            True if error should be retried, False otherwise
        """
        error_type = cls.classify_error(error_message, http_status)
        return error_type == ErrorType.TRANSIENT


class SimpleQuotaManager:
    """
    Thread-safe token bucket quota manager for API rate limiting.
    
    Uses a token bucket algorithm to enforce rate limits across concurrent operations.
    """
    
    def __init__(self, rate: int, per_seconds: int = 60):
        """
        Initialize quota manager.
        
        Args:
            rate: Number of tokens allowed per time period
            per_seconds: Time period in seconds (default: 60)
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self.allowance = float(rate)
        self.last_check = time.time()
        self.lock = Lock()
        self.consumed_count = 0
        self.throttle_count = 0
    
    def consume(self, tokens: int = 1, wait: bool = True) -> bool:
        """
        Consume tokens from the quota.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            wait: If True, wait for tokens to be available; if False, return immediately
            
        Returns:
            True if tokens were consumed, False if quota exceeded and wait=False
        """
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_check
                self.last_check = now
                
                # Refill tokens based on elapsed time
                self.allowance += elapsed * (self.rate / self.per_seconds)
                
                # Cap at maximum rate
                if self.allowance > self.rate:
                    self.allowance = self.rate
                
                # Check if we have enough tokens
                if self.allowance >= tokens:
                    self.allowance -= tokens
                    self.consumed_count += tokens
                    return True
                
                # Not enough tokens
                if not wait:
                    self.throttle_count += 1
                    return False
            
            # Wait for tokens to refill
            self.throttle_count += 1
            sleep_time = (tokens - self.allowance) * (self.per_seconds / self.rate)
            time.sleep(min(sleep_time, 1.0))  # Sleep at most 1 second at a time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get quota manager statistics."""
        with self.lock:
            return {
                'rate': self.rate,
                'per_seconds': self.per_seconds,
                'current_allowance': self.allowance,
                'consumed_count': self.consumed_count,
                'throttle_count': self.throttle_count,
            }


class RetryHelper:
    """Helper for executing functions with retry logic and exponential backoff."""
    
    @staticmethod
    def retry_with_backoff(
        func: Callable,
        attempts: int = 3,
        base: float = 0.5,
        factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        error_classifier: Optional[ErrorClassifier] = None,
    ) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        Args:
            func: Function to execute
            attempts: Maximum number of attempts
            base: Base delay in seconds
            factor: Exponential backoff factor
            max_delay: Maximum delay between retries
            jitter: Whether to add random jitter to delays
            error_classifier: Optional error classifier for smart retry
            
        Returns:
            Result of successful function execution
            
        Raises:
            Last exception if all attempts fail
        """
        last_exception = None
        
        for attempt in range(1, attempts + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if error_classifier:
                    error_msg = str(e)
                    if not error_classifier.should_retry(error_msg):
                        # Permanent error - don't retry
                        raise
                
                # Don't sleep after last attempt
                if attempt >= attempts:
                    break
                
                # Calculate backoff delay
                delay = min(base * (factor ** (attempt - 1)), max_delay)
                
                # Add jitter if requested
                if jitter:
                    delay += random.uniform(0, delay * 0.2)
                
                time.sleep(delay)
        
        # All attempts failed
        raise last_exception


class CheckpointManagerV2:
    """
    Enhanced checkpoint manager for v2.0 with per-paper tracking.
    
    Provides atomic writes, per-paper status tracking, and dry-run support.
    """
    
    def __init__(self, checkpoint_file: str, dry_run: bool = False):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Path to checkpoint file
            dry_run: If True, simulate checkpoint operations without writing
        """
        self.checkpoint_file = checkpoint_file
        self.dry_run = dry_run
        self.lock = Lock()  # Add lock for thread safety
        self.data: Dict[str, Any] = {
            'run_id': self._generate_run_id(),
            'version': '2.0.0',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'papers': {},
            'config': {},
            'stats': {
                'total_papers': 0,
                'completed_papers': 0,
                'failed_papers': 0,
                'retries': 0,
            }
        }
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        unique_id = hashlib.md5(f"{timestamp}{os.getpid()}".encode()).hexdigest()[:8]
        return f"{timestamp}_{unique_id}"
    
    def load(self) -> bool:
        """
        Load checkpoint from file.
        
        Returns:
            True if checkpoint was loaded, False otherwise
        """
        if not Path(self.checkpoint_file).exists():
            return False
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except Exception:
            return False
    
    def save(self):
        """Save checkpoint to file atomically."""
        with self.lock:  # Ensure thread-safe writes
            if self.dry_run:
                print(f"[DRY-RUN] Would save checkpoint to {self.checkpoint_file}")
                return
            
            self.data['last_updated'] = datetime.now().isoformat()
            
            # Ensure directory exists
            checkpoint_path = Path(self.checkpoint_file)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic write: write to temp file, then rename
            tmp_file = checkpoint_path.with_suffix('.tmp')
            try:
                with tmp_file.open('w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic rename
                tmp_file.replace(self.checkpoint_file)
            except Exception as e:
                if tmp_file.exists():
                    tmp_file.unlink()
                raise e
    
    def update_paper_status(
        self,
        paper_id: str,
        stage: str,
        stages_completed: Optional[List[str]] = None,
        error: Optional[str] = None
    ):
        """
        Update status for a specific paper.
        
        Args:
            paper_id: Unique paper identifier
            stage: Current stage ('not_started', 'in_progress', 'completed', 'failed')
            stages_completed: List of completed stage names
            error: Optional error message if stage failed
        """
        if paper_id not in self.data['papers']:
            self.data['papers'][paper_id] = {
                'stage': 'not_started',
                'stages': {},
                'retries': 0,
                'started_at': None,
                'completed_at': None,
            }
        
        paper = self.data['papers'][paper_id]
        paper['stage'] = stage
        
        if stages_completed:
            for stage_name in stages_completed:
                if stage_name not in paper['stages']:
                    paper['stages'][stage_name] = datetime.now().isoformat()
        
        if error:
            paper['last_error'] = error
            if 'errors' not in paper:
                paper['errors'] = []
            paper['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'message': error[:500]  # Truncate long errors
            })
        
        if stage == 'in_progress' and not paper['started_at']:
            paper['started_at'] = datetime.now().isoformat()
        
        if stage == 'completed':
            paper['completed_at'] = datetime.now().isoformat()
            self.data['stats']['completed_papers'] += 1
        
        if stage == 'failed':
            self.data['stats']['failed_papers'] += 1
        
        self.save()
    
    def increment_retries(self, paper_id: str):
        """Increment retry count for a paper."""
        if paper_id in self.data['papers']:
            self.data['papers'][paper_id]['retries'] += 1
            self.data['stats']['retries'] += 1
            self.save()
    
    def get_paper_status(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific paper."""
        return self.data['papers'].get(paper_id)
    
    def get_incomplete_papers(self) -> List[str]:
        """Get list of papers that are not completed."""
        incomplete = []
        for paper_id, status in self.data['papers'].items():
            if status['stage'] not in ['completed', 'failed']:
                incomplete.append(paper_id)
        return incomplete


class ParallelPipelineCoordinator:
    """
    Coordinates parallel execution of pipeline stages across multiple papers.
    
    Uses ThreadPoolExecutor for IO-bound operations (API calls).
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        quota_manager: Optional[SimpleQuotaManager] = None,
        checkpoint_manager: Optional[CheckpointManagerV2] = None,
        dry_run: bool = False,
    ):
        """
        Initialize parallel coordinator.
        
        Args:
            max_workers: Maximum number of concurrent workers
            quota_manager: Optional quota manager for rate limiting
            checkpoint_manager: Optional checkpoint manager for progress tracking
            dry_run: If True, simulate execution without side effects
        """
        self.max_workers = max_workers
        self.quota_manager = quota_manager
        self.checkpoint = checkpoint_manager
        self.dry_run = dry_run
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0,
        }
    
    def process_papers_parallel(
        self,
        papers: List[str],
        process_func: Callable[[str], Dict[str, Any]],
        use_threads: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple papers in parallel.
        
        Args:
            papers: List of paper identifiers
            process_func: Function to process a single paper
            use_threads: If True, use ThreadPoolExecutor; if False, use ProcessPoolExecutor
            
        Returns:
            List of results for each paper
        """
        results = []
        
        # Choose executor based on use_threads flag
        ExecutorClass = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
        
        with ExecutorClass(max_workers=self.max_workers) as executor:
            # Submit all papers
            futures = {
                executor.submit(self._process_paper_with_quota, paper, process_func): paper
                for paper in papers
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                paper = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.get('status') == 'success':
                        self.stats['successful'] += 1
                    else:
                        self.stats['failed'] += 1
                    
                    if self.checkpoint:
                        stage = 'completed' if result.get('status') == 'success' else 'failed'
                        self.checkpoint.update_paper_status(
                            paper,
                            stage,
                            stages_completed=result.get('stages_completed', []),
                            error=result.get('error')
                        )
                
                except Exception as e:
                    results.append({
                        'paper': paper,
                        'status': 'error',
                        'error': str(e),
                    })
                    self.stats['failed'] += 1
                    
                    if self.checkpoint:
                        self.checkpoint.update_paper_status(
                            paper,
                            'failed',
                            error=str(e)
                        )
                
                self.stats['total_processed'] += 1
        
        return results
    
    def _process_paper_with_quota(
        self,
        paper: str,
        process_func: Callable[[str], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a single paper with quota management.
        
        Args:
            paper: Paper identifier
            process_func: Function to process the paper
            
        Returns:
            Result dictionary
        """
        # Consume quota before processing
        if self.quota_manager:
            self.quota_manager.consume(wait=True)
        
        # Mark as in progress
        if self.checkpoint:
            self.checkpoint.update_paper_status(paper, 'in_progress')
        
        # Process paper
        if self.dry_run:
            print(f"[DRY-RUN] Would process paper: {paper}")
            return {
                'paper': paper,
                'status': 'success',
                'dry_run': True,
            }
        
        return process_func(paper)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.stats.copy()


def create_v2_config_defaults() -> Dict[str, Any]:
    """Create default configuration for v2.0 features."""
    return {
        'max_workers': 4,
        'enable_parallel': False,  # Safety: disabled by default
        'checkpoint_file': 'pipeline_checkpoint.json',
        'retry': {
            'attempts': 3,
            'base': 0.5,
            'factor': 2.0,
            'max_delay': 60.0,
            'enable_jitter': True,
        },
        'quota': {
            'gemini_api': {
                'rate': 60,
                'per_seconds': 60,
            }
        },
        'feature_flags': {
            'enable_parallel_processing': False,
            'enable_quota_management': True,
            'enable_smart_retry': True,
        }
    }
