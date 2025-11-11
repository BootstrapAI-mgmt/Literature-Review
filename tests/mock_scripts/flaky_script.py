#!/usr/bin/env python3
"""
Mock script that simulates flaky behavior.

Fails 50% of the time with a retryable error (connection timeout).
Used for testing retry logic.
"""

import sys
import random

# Simulate flaky behavior (fails 50% of time)
if random.random() < 0.5:
    print("Simulated transient failure: Connection timeout", file=sys.stderr)
    sys.exit(1)
else:
    print("Success!")
    sys.exit(0)
