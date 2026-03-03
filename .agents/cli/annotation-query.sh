#!/usr/bin/env bash
# .agents/cli/annotation-query.sh
# Source: Distilled from MCP-to-CLI+Skills conversion
# Date: 2026-03-03
#
# Replaces: annotation-query MCP server (annotation-server/annotation_mcp.py)
#
# Prerequisites:
#   - Python 3.9+ with sqlite3
#   - Annotation database built (run annotation-server/build_db.py first)
#
# Usage:
#   .agents/cli/annotation-query.sh {search|paper|stats|rebuild} [args]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DB_PATH="${ANNOTATION_DB:-$REPO_ROOT/annotation-server/annotations.db}"
ACTION="${1:-help}"
shift || true

case "$ACTION" in
    search)
        QUERY="${1:?Usage: $0 search <query>}"
        echo "=== Searching annotations: $QUERY ==="
        python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cursor = conn.execute(
    'SELECT paper_id, section, content FROM annotations WHERE content LIKE ?',
    ('%$QUERY%',)
)
for row in cursor:
    print(f'[{row[0]}] {row[1]}: {row[2][:200]}...')
conn.close()
"
        ;;
    paper)
        PAPER_ID="${1:?Usage: $0 paper <paper_id>}"
        echo "=== Annotations for paper: $PAPER_ID ==="
        python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cursor = conn.execute(
    'SELECT section, content FROM annotations WHERE paper_id = ?',
    ('$PAPER_ID',)
)
for row in cursor:
    print(f'[{row[0]}] {row[1]}')
conn.close()
"
        ;;
    stats)
        echo "=== Annotation Database Stats ==="
        python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
    print(f'  {t[0]}: {count} rows')
conn.close()
"
        ;;
    rebuild)
        echo "=== Rebuilding Annotation Database ==="
        python3 "$REPO_ROOT/annotation-server/build_db.py"
        echo "  Done."
        ;;
    *)
        echo "Usage: $0 {search|paper|stats|rebuild} [args]"
        echo ""
        echo "Actions:"
        echo "  search <query>     Search annotations by content"
        echo "  paper <paper_id>   Get all annotations for a paper"
        echo "  stats              Show database statistics"
        echo "  rebuild            Rebuild database from source data"
        echo ""
        echo "Database: $DB_PATH"
        exit 1
        ;;
esac
