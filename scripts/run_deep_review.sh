#!/bin/bash
# Convenience wrapper for Deep Reviewer workflow

set -e

echo "=== Deep Reviewer Workflow ==="
echo ""

# Check if directions file exists
if [ ! -f "gap_analysis_output/deep_review_directions.json" ]; then
    echo "⚠️  No deep_review_directions.json found"
    echo "   Generating for top 10 gaps..."
    python scripts/generate_deep_review_directions.py --top 10
    echo ""
fi

# Show what will be analyzed
echo "📋 Deep Review Directions:"
python -c "
import json
with open('gap_analysis_output/deep_review_directions.json', 'r') as f:
    dirs = json.load(f)
    print(f'  {len(dirs)} gaps targeted')
    for sub_req, data in list(dirs.items())[:5]:
        print(f'  - {sub_req}: {data[\"current_completeness\"]:.0f}% complete, {len(data[\"contributing_papers\"])} papers')
    if len(dirs) > 5:
        print(f'  ... and {len(dirs) - 5} more')
"
echo ""

# Confirm
read -p "Continue with Deep Review? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Run Deep Reviewer
echo ""
echo "🔍 Running Deep Reviewer..."
python -m literature_review.reviewers.deep_reviewer

echo ""
echo "⚖️  Running Judge on new claims..."
python -m literature_review.analysis.judge

echo ""
echo "📊 Re-running Gap Analysis..."
python -m literature_review.orchestrator

echo ""
echo "✅ Deep Review Complete!"
echo "   Check gap_analysis_output/ for updated analysis"
