#!/bin/bash
#
# Start local n8n server in the Codespace
#
# This script starts n8n locally in the codespace for development/testing.
# For production, use an external n8n instance.
#
# Usage:
#   ./start-n8n-local.sh              # Start n8n in foreground
#   ./start-n8n-local.sh --background # Start in background
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKGROUND=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --background|-b)
            BACKGROUND=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --background, -b  Run n8n in background"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "n8n will be available at http://localhost:5678"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if npm dependencies are installed
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

echo "Starting n8n server..."
echo "  URL: http://localhost:5678"
echo ""

if [ "$BACKGROUND" = true ]; then
    # Background mode - log to file
    LOG_FILE="$SCRIPT_DIR/n8n.log"
    nohup npm start > "$LOG_FILE" 2>&1 &
    echo $! > "$SCRIPT_DIR/n8n.pid"
    echo "n8n started in background (PID: $(cat "$SCRIPT_DIR/n8n.pid"))"
    echo "Logs: $LOG_FILE"
    echo ""
    echo "To stop: kill \$(cat $SCRIPT_DIR/n8n.pid)"
else
    # Foreground mode
    npm start
fi
