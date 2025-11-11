#!/usr/bin/env python3
"""
Mock script that always fails with a permanent error.

Used for testing that permanent errors are not retried.
"""

import sys

print("SyntaxError: invalid syntax on line 42", file=sys.stderr)
sys.exit(1)
