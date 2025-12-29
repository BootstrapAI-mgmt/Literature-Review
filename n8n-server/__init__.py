"""
n8n Server Integration Package

This package provides tools for interacting with n8n workflow automation
from GitHub Codespaces and other environments.

Modules:
    bridge: Python API bridge for n8n (CLI & library)
    n8n_mcp_server: MCP server for AI assistant integration

Usage:
    # CLI
    python -m n8n_server.bridge health
    python -m n8n_server.bridge list
    
    # Python
    from n8n_server.bridge import N8nBridge
    bridge = N8nBridge()
    workflows = bridge.list_workflows()
"""

from pathlib import Path

__version__ = "1.0.0"
__all__ = ["N8nBridge"]

# Package directory
PACKAGE_DIR = Path(__file__).parent
