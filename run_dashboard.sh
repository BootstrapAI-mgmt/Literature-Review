#!/bin/bash
# Run the Web Dashboard locally
#
# Usage:
#   ./run_dashboard.sh [--port PORT] [--api-key KEY]

# Default values
PORT=8000
API_KEY="dev-key-change-in-production"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--port PORT] [--api-key KEY]"
            echo ""
            echo "Options:"
            echo "  --port PORT       Port to run on (default: 8000)"
            echo "  --api-key KEY     API key for authentication (default: dev-key-change-in-production)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help for usage information"
            exit 1
            ;;
    esac
done

# Check if requirements are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dashboard requirements..."
    pip install -r requirements-dashboard.txt
fi

# Set environment variable
export DASHBOARD_API_KEY="$API_KEY"

# Create workspace directories
mkdir -p workspace/uploads workspace/jobs workspace/status workspace/logs

# Run the server
echo "Starting Literature Review Dashboard..."
echo "Port: $PORT"
echo "API Key: $API_KEY"
echo ""
echo "Open http://localhost:$PORT in your browser"
echo "Press Ctrl+C to stop"
echo ""

uvicorn webdashboard.app:app --host 0.0.0.0 --port "$PORT" --reload
