#!/bin/bash
#
# n8n Integration Bootstrap for GitHub Codespaces
#
# This script quickly sets up the n8n integration in any new codespace.
# Run this once when opening a fresh codespace if the automatic setup didn't run.
#
# Usage:
#   ./bootstrap-n8n.sh
#   source ./bootstrap-n8n.sh  # To also export env vars in current shell
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       n8n Integration Bootstrap for Literature Review        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Set N8N_API_URL if not already set
if [ -z "$N8N_API_URL" ] || [ "$N8N_API_URL" = "http" ]; then
    export N8N_API_URL="https://gitlitreview.app.n8n.cloud/api/v1"
    echo "✓ Set N8N_API_URL=$N8N_API_URL"
else
    echo "✓ N8N_API_URL already set: $N8N_API_URL"
fi

# Step 2: Check for N8N_API_KEY
if [ -z "$N8N_API_KEY" ]; then
    echo ""
    echo "⚠ N8N_API_KEY not found in environment."
    echo ""
    echo "  To fix this, add the secret to your Codespace:"
    echo "  1. Go to: https://github.com/BootstrapAI-mgmt/Literature-Review/settings/secrets/codespaces"
    echo "  2. Add secret: N8N_API_KEY"
    echo "  3. Value: Get from n8n Settings > Personal API Keys"
    echo "  4. Rebuild the codespace or run: source /etc/environment"
    echo ""
    HAS_KEY=false
else
    KEY_LEN=${#N8N_API_KEY}
    echo "✓ N8N_API_KEY found (${KEY_LEN} chars)"
    HAS_KEY=true
fi

# Step 3: Ensure npm dependencies are installed
if [ ! -d "$REPO_ROOT/n8n-server/node_modules" ]; then
    echo ""
    echo "Installing npm dependencies..."
    cd "$REPO_ROOT/n8n-server" && npm install --silent
    echo "✓ npm dependencies installed"
fi

# Step 4: Make scripts executable
chmod +x "$REPO_ROOT/n8n-server/"*.sh 2>/dev/null || true
chmod +x "$REPO_ROOT/n8n-server/"*.py 2>/dev/null || true

# Step 5: Test connection if we have the key
if [ "$HAS_KEY" = true ]; then
    echo ""
    echo "Testing n8n connection..."
    if python3 "$REPO_ROOT/n8n-server/bridge.py" health 2>/dev/null; then
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║                    ✅ SETUP COMPLETE                         ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Available commands:"
        echo "  python3 n8n-server/bridge.py list        # List workflows"
        echo "  python3 n8n-server/bridge.py executions  # View executions"
        echo "  python3 n8n-server/bridge.py health      # Check status"
        echo ""
    else
        echo ""
        echo "⚠ Connection test failed. Check your API key."
    fi
else
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              ⚠ SETUP INCOMPLETE - NEED API KEY               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
fi

# Export for subshells
export N8N_API_URL
