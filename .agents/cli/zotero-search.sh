#!/usr/bin/env bash
# .agents/cli/zotero-search.sh
# Source: Distilled from MCP-to-CLI+Skills conversion
# Date: 2026-03-03
#
# Replaces: zotero MCP server (simple lookups only)
# Note: Complex Zotero browsing/discovery still uses the zotero MCP server
#
# Prerequisites:
#   - Python 3.9+
#   - Zotero local database accessible
#   - ZOTERO_LOCAL=true in environment
#
# Usage:
#   .agents/cli/zotero-search.sh {search|get|tags|recent} [args]

set -euo pipefail

export ZOTERO_LOCAL="${ZOTERO_LOCAL:-true}"
ACTION="${1:-help}"
shift || true

case "$ACTION" in
    search)
        QUERY="${1:?Usage: $0 search <query>}"
        echo "=== Searching Zotero: $QUERY ==="
        python3 -c "
import json, os, sys
# Search local Zotero data files
data_dir = 'data'
if os.path.exists('all_bib_entries.json'):
    with open('all_bib_entries.json') as f:
        entries = json.load(f)
    matches = [e for e in entries if '$QUERY'.lower() in json.dumps(e).lower()]
    for m in matches[:20]:
        title = m.get('title', 'No title')
        author = m.get('author', 'Unknown')
        year = m.get('year', '?')
        print(f'  [{year}] {author}: {title}')
    print(f'  ({len(matches)} matches total)')
else:
    print('  all_bib_entries.json not found. Run zotero_pipeline.py first.')
"
        ;;
    get)
        KEY="${1:?Usage: $0 get <citation_key>}"
        echo "=== Zotero Entry: $KEY ==="
        python3 -c "
import json
with open('all_bib_entries.json') as f:
    entries = json.load(f)
matches = [e for e in entries if e.get('ID', '') == '$KEY' or e.get('key', '') == '$KEY']
if matches:
    print(json.dumps(matches[0], indent=2))
else:
    print('  Not found: $KEY')
"
        ;;
    tags)
        echo "=== Zotero Tags ==="
        python3 -c "
import json
from collections import Counter
with open('all_bib_entries.json') as f:
    entries = json.load(f)
tags = Counter()
for e in entries:
    for t in e.get('tags', []):
        tags[t if isinstance(t, str) else t.get('tag', '')] += 1
for tag, count in tags.most_common(30):
    print(f'  {tag}: {count}')
"
        ;;
    recent)
        LIMIT="${1:-10}"
        echo "=== Recent Entries (last $LIMIT) ==="
        python3 -c "
import json
with open('all_bib_entries.json') as f:
    entries = json.load(f)
sorted_entries = sorted(entries, key=lambda e: e.get('year', '0'), reverse=True)
for e in sorted_entries[:$LIMIT]:
    title = e.get('title', 'No title')
    author = e.get('author', 'Unknown')
    year = e.get('year', '?')
    print(f'  [{year}] {author}: {title}')
"
        ;;
    *)
        echo "Usage: $0 {search|get|tags|recent} [args]"
        echo ""
        echo "Actions:"
        echo "  search <query>     Search by keyword across all fields"
        echo "  get <key>          Get full entry by citation key"
        echo "  tags               List top 30 tags by frequency"
        echo "  recent [n]         Show n most recent entries (default: 10)"
        echo ""
        echo "Note: For complex Zotero browsing, use the zotero MCP server"
        exit 1
        ;;
esac
