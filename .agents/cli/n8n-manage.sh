#!/usr/bin/env bash
# .agents/cli/n8n-manage.sh
# Source: Distilled from MCP-to-CLI+Skills conversion
# Date: 2026-03-03
#
# Wraps n8n-server/scripts/ for common n8n management operations
#
# Prerequisites:
#   - Python 3.9+
#   - n8n running locally on port 5678
#   - .env file with N8N_API_KEY, GITHUB_TOKEN
#
# Usage:
#   .agents/cli/n8n-manage.sh {verify|deploy|sync-export|sync-import|services|health} [args]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/n8n-server/scripts"
ACTION="${1:-help}"
shift || true

case "$ACTION" in
    verify)
        echo "=== Verifying n8n Environment ==="
        python3 "$SCRIPTS_DIR/verify_env.py"
        ;;
    deploy)
        echo "=== Deploying to n8n ==="
        python3 "$SCRIPTS_DIR/deploy.py" "$@"
        ;;
    sync-export)
        echo "=== Exporting Workflows from n8n ==="
        python3 "$SCRIPTS_DIR/sync_workflows.py" --export
        ;;
    sync-import)
        echo "=== Importing Workflows to n8n ==="
        python3 "$SCRIPTS_DIR/sync_workflows.py" --import
        ;;
    patch)
        echo "=== Patching Workflows with Env Vars ==="
        python3 "$SCRIPTS_DIR/sync_workflows_api.py"
        ;;
    services)
        SUBACTION="${1:-status}"
        shift || true
        echo "=== n8n Services: $SUBACTION ==="
        python3 "$SCRIPTS_DIR/manage_services.py" "$SUBACTION" "$@"
        ;;
    health)
        echo "=== n8n Health Check ==="
        curl -sf "http://localhost:5678/healthz" > /dev/null 2>&1 \
            && echo "  n8n is running on port 5678" \
            || echo "  n8n is NOT responding on port 5678"
        ;;
    *)
        echo "Usage: $0 {verify|deploy|sync-export|sync-import|patch|services|health} [args]"
        echo ""
        echo "Actions:"
        echo "  verify        Check environment prerequisites"
        echo "  deploy        Deploy changes to n8n (--no-pull, --restart)"
        echo "  sync-export   Export all workflows from n8n to JSON"
        echo "  sync-import   Import all workflows from JSON to n8n"
        echo "  patch         Patch workflows with repository env vars"
        echo "  services      Manage n8n services (start|stop|status)"
        echo "  health        Quick health check on n8n server"
        echo ""
        echo "Scripts directory: $SCRIPTS_DIR"
        exit 1
        ;;
esac
