#!/bin/bash
# run_e2e_tests.sh
# Tier 3 E2E Test Runner
# Per Master Validation Plan V2.0.0 Phase 4

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIER3_DIR="$REPO_ROOT/tests/tier3"
REPORTS_DIR="$REPO_ROOT/reports"

echo "=============================================="
echo -e "${BLUE}Tier 3 E2E Test Runner${NC}"
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
    
    echo -e "${YELLOW}Running E2E tests in $mode mode...${NC}"
    echo ""
    
    cd "$REPO_ROOT"
    
    case $mode in
        "offline")
            # Offline mode: Run only offline tests
            python -m pytest "$TIER3_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "e2e" \
                -k "Offline or offline or STATE" \
                $extra_args
            ;;
        "live")
            # Live mode: Run all E2E tests including live n8n tests
            echo -e "${YELLOW}NOTE: This mode requires active n8n Cloud connection${NC}"
            python -m pytest "$TIER3_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "e2e" \
                $extra_args
            ;;
        "chain")
            # Chain mode: Run only workflow chain tests
            python -m pytest "$TIER3_DIR/test_doc_chain_e2e.py" -v \
                -o "addopts=" \
                --tb=short \
                $extra_args
            ;;
        "pr")
            # PR mode: Run only PR merge chain tests
            python -m pytest "$TIER3_DIR/test_pr_merge_chain.py" -v \
                -o "addopts=" \
                --tb=short \
                $extra_args
            ;;
        "file")
            # File mode: Run only new file detection tests
            python -m pytest "$TIER3_DIR/test_new_file_chain.py" -v \
                -o "addopts=" \
                --tb=short \
                $extra_args
            ;;
        "report")
            # Report mode: Generate HTML report
            python -m pytest "$TIER3_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "e2e" \
                --html="$REPORTS_DIR/tier3_e2e_report.html" \
                --self-contained-html \
                $extra_args 2>/dev/null || \
            python -m pytest "$TIER3_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "e2e" \
                $extra_args
            ;;
        *)
            # Default: Run all E2E tests
            python -m pytest "$TIER3_DIR" -v \
                -o "addopts=" \
                --tb=short \
                -m "e2e" \
                $extra_args
            ;;
    esac
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ E2E tests completed successfully!${NC}"
    else
        echo ""
        echo -e "${RED}❌ Some E2E tests failed (exit code: $exit_code)${NC}"
    fi
    
    return $exit_code
}

# Parse command line arguments
MODE="${1:-default}"
shift 2>/dev/null || true

case $MODE in
    "offline"|"live"|"chain"|"pr"|"file"|"report"|"default")
        run_tests "$MODE" "$@"
        ;;
    "-h"|"--help")
        echo "Usage: $0 [mode] [pytest args...]"
        echo ""
        echo "Modes:"
        echo "  offline  - Run only offline tests (no n8n required)"
        echo "  live     - Run all tests including live n8n tests"
        echo "  chain    - Run only doc chain workflow tests"
        echo "  pr       - Run only PR merge chain tests"
        echo "  file     - Run only new file detection tests"
        echo "  report   - Generate HTML report"
        echo "  default  - Run all E2E tests"
        echo ""
        echo "Examples:"
        echo "  $0 offline"
        echo "  $0 live --verbose"
        echo "  $0 chain"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
