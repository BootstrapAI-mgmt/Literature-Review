"""Sliding-window hourly rate limiter for subscription-backed LLM paths.

Used by the Claude Code (`claude-agent-sdk`) provider to stay within
Max-plan rate budgets while sharing the account with interactive use.

Configuration precedence (highest first):
  1. Explicit ``limit_per_hour`` argument to ``HourlyRateLimiter``.
  2. ``CLAUDE_CODE_RPH`` environment variable.
  3. ``ModelConfig.requests_per_hour`` (set on the model definition).
  4. Default of 18 requests/hour.

The limiter keeps a deque of call timestamps; ``acquire`` drops anything
older than 60 minutes, and if the remaining window is at capacity it
sleeps until the oldest timestamp ages out. Calls are thread-safe.

This is intentionally *continuous* (sliding window) rather than periodic
(burst then long sleep) so that:

  - Interactive Claude Code use on the same account isn't interrupted by
    multi-minute idle gaps from the pipeline.
  - Throughput is predictable: never more than ``limit_per_hour`` calls
    in any rolling 60-minute window.
  - Bursting is impossible — the API spec for Max-plan windows is
    enforced at the application layer here.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)


_DEFAULT_RPH = 18  # comfortable for ~10-18 single-eval papers/hr with margin


class HourlyRateLimiter:
    """Sliding-window per-hour rate limiter.

    Args:
        limit_per_hour: Maximum calls allowed in any rolling 60-minute
            window. Pass 0 to disable (the limiter becomes a no-op).
        name: Human-readable label used in log messages.
    """

    def __init__(self, limit_per_hour: int | None = None, name: str = "claude_code"):
        if limit_per_hour is None:
            env = os.environ.get("CLAUDE_CODE_RPH")
            try:
                limit_per_hour = int(env) if env else _DEFAULT_RPH
            except ValueError:
                logger.warning(
                    "Invalid CLAUDE_CODE_RPH=%r; falling back to default %d/hr",
                    env, _DEFAULT_RPH,
                )
                limit_per_hour = _DEFAULT_RPH
        self.limit = max(0, limit_per_hour)
        self.name = name
        self._window: Deque[float] = deque()
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    def _prune(self, now: float) -> None:
        cutoff = now - 3600
        while self._window and self._window[0] < cutoff:
            self._window.popleft()

    def remaining(self) -> int:
        """How many calls are left in the current sliding window."""
        if not self.enabled:
            return 2 ** 31
        with self._lock:
            self._prune(time.time())
            return max(0, self.limit - len(self._window))

    def acquire(self) -> float:
        """Block until a slot is available; return the wait time in seconds.

        Returns 0.0 immediately if the limiter is disabled or the window
        has capacity.
        """
        if not self.enabled:
            return 0.0
        total_wait = 0.0
        while True:
            with self._lock:
                now = time.time()
                self._prune(now)
                if len(self._window) < self.limit:
                    self._window.append(now)
                    return total_wait
                oldest = self._window[0]
                # +1s margin so the oldest entry is definitely outside the window
                wait = max(0.0, 3600 - (now - oldest) + 1.0)
            logger.info(
                "[rate_limiter:%s] hourly cap %d/h reached; sleeping %.1fs",
                self.name, self.limit, wait,
            )
            time.sleep(wait)
            total_wait += wait

    def reset(self) -> None:
        """Clear the sliding window (useful for tests)."""
        with self._lock:
            self._window.clear()
