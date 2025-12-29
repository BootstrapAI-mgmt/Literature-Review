#!/bin/bash
#
# Start n8n MCP Server for Codespace
#
# This script starts the Python-based n8n MCP server that allows
# AI coding assistants to interact with n8n workflows.
#
# Usage:
#   ./start-mcp.sh                    # Uses environment variables
#   ./start-mcp.sh --api-key=xxx      # Provide API key
#   ./start-mcp.sh --remote=url       # Connect to remote n8n
#
# Environment Variables:
#   N8N_API_URL - URL to n8n API (default: http://localhost:5678/api/v1)
#   N8N_API_KEY - n8n API key (required)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-key=*)
            export N8N_API_KEY="${1#*=}"
            shift
            ;;
        --api-url=*|--remote=*)
            export N8N_API_URL="${1#*=}"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --api-key=KEY    Set n8n API key"
            echo "  --api-url=URL    Set n8n API URL (default: http://localhost:5678/api/v1)"
            echo "  --help           Show this help message"
            echo ""
            echo "Environment:"
            echo "  N8N_API_URL      n8n API URL"
            echo "  N8N_API_KEY      n8n API key (required)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for API key
if [ -z "$N8N_API_KEY" ]; then
    echo "Error: N8N_API_KEY is required"
    echo "Set it via environment variable or --api-key=xxx"
    exit 1
fi

# Set default URL if not provided
export N8N_API_URL="${N8N_API_URL:-http://localhost:5678/api/v1}"

echo "Starting n8n MCP Server..."
echo "  API URL: $N8N_API_URL"
echo ""

# Run the MCP server
exec python3 "$SCRIPT_DIR/n8n_mcp_server.py"
