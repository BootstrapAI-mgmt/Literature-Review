#!/bin/bash
#
# Codespace Setup for n8n Integration
#
# This script sets up the n8n integration in a GitHub Codespace.
# Run this once after opening the codespace.
#
# Usage:
#   ./setup-codespace.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  n8n Integration Setup for Codespace"
echo "=========================================="
echo ""

# Check Node.js
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    echo "  ✓ Node.js $(node --version)"
else
    echo "  ✗ Node.js not found!"
    exit 1
fi

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    echo "  ✓ Python $(python3 --version 2>&1 | cut -d' ' -f2)"
else
    echo "  ✗ Python 3 not found!"
    exit 1
fi

echo ""
echo "Installing npm dependencies..."
cd "$SCRIPT_DIR"
npm install

echo ""
echo "Making scripts executable..."
chmod +x "$SCRIPT_DIR/start-mcp.sh"
chmod +x "$SCRIPT_DIR/start-n8n-local.sh"
chmod +x "$SCRIPT_DIR/setup-codespace.sh"
chmod +x "$SCRIPT_DIR/bridge.py"
chmod +x "$SCRIPT_DIR/n8n_mcp_server.py"

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start local n8n server (optional for testing):"
echo "   cd n8n-server && ./start-n8n-local.sh"
echo ""
echo "2. Generate an API key in n8n:"
echo "   - Open http://localhost:5678"
echo "   - Go to Settings > Personal API Keys"
echo "   - Create and copy a new API key"
echo ""
echo "3. Set environment variables:"
echo "   export N8N_API_URL='http://localhost:5678/api/v1'"
echo "   export N8N_API_KEY='your-api-key'"
echo ""
echo "4. Test the bridge:"
echo "   python3 n8n-server/bridge.py health"
echo "   python3 n8n-server/bridge.py list"
echo ""
echo "5. For remote n8n server, set N8N_API_URL to the remote URL"
echo ""
