#!/bin/bash
# run_integration_tests.sh
# Tier 2 Integration Test Runner
# Per Master Validation Plan V2.0.0 Appendix B.2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIER2_DIR="$REPO_ROOT/tests/tier2"
REPORTS_DIR="$REPO_ROOT/reports"

echo "=============================================="
echo "Tier 2 Integration Test Runner"
echo "=============================================="
echo ""

# Check if n8n is configured
N8N_URL="${N8N_WEBHOOK_URL:-https://gitlitreview.app.n8n.cloud/webhook}"
echo "n8n Webhook URL: $N8N_URL"
echo ""

# Create reports directory if needed
mkdir -p "$REPORTS_DIR"

# Run tests with different modes
run_tests() {
    local mode=$1
    local extra_args="${@:2}"
    
    echo -e "${YELLOW}Running in $mode mode...${NC}"
    echo ""
    
    cd "$REPO_ROOT"
    
    case $mode in
        "offline")
            # Offline mode: Run all tests, expect skips for n8n-dependent tests
            python -m pytest "$TIER2_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "integration" \
                $extra_args
            ;;
        "online")
            # Online mode: Run with n8n Cloud connection
            python -m pytest "$TIER2_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "integration" \
                --strict-markers \
                $extra_args
            ;;
        "report")
            # Report mode: Generate HTML/JSON reports
            python -m pytest "$TIER2_DIR" -v \
                -o "addopts=" \
                --tb=short \
                --html="$REPORTS_DIR/tier2_integration_report.html" \
                --self-contained-html \
                $extra_args 2>/dev/null || \
            python -m pytest "$TIER2_DIR" -v \
                -o "addopts=" \
                --tb=short \
                $extra_args
            ;;
        "quick")
            # Quick mode: Run only endpoint availability tests
            python -m pytest "$TIER2_DIR/test_endpoint_availability.py" -v \
                -o "addopts=" \
                --tb=line \
                $extra_args
            ;;
        *)
            # Default: Run all tests
            python -m pytest "$TIER2_DIR" -v \
                -o "addopts=" \
                --tb=short \
                $extra_args
            ;;
    esac
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ All tests passed!${NC}"
    else
        echo ""
        echo -e "${RED}❌ Some tests failed (exit code: $exit_code)${NC}"
    fi
    
    return $exit_code
}

# Parse command line arguments
MODE="${1:-default}"
shift 2>/dev/null || true

case $MODE in
    "offline"|"online"|"report"|"quick"|"default")
        run_tests "$MODE" "$@"
        ;;
    "-h"|"--help")
        echo "Usage: $0 [mode] [pytest args...]"
        echo ""
        echo "Modes:"
        echo "  offline  - Run tests expecting n8n to be unavailable"
        echo "  online   - Run tests with live n8n connection"
        echo "  report   - Generate HTML report"
        echo "  quick    - Run only endpoint availability tests"
        echo "  default  - Run all tests"
        echo ""
        echo "Examples:"
        echo "  $0 offline"
        echo "  $0 online --verbose"
        echo "  $0 report"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
