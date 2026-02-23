"""
Rebuild review_version_history.json from the database CSV.

The current version history file is corrupted and massively bloated (192MB with 38K+
duplicate entries for ~900 papers). This script rebuilds a clean version history
from the authoritative database CSV, creating one version entry per paper.
"""

import csv
import json
import os
from datetime import datetime

DATABASE_CSV = "neuromorphic-research_database.csv"
OUTPUT_FILE = "review_version_history_REBUILT.json"
CORRUPTED_FILE = "review_version_history.json"

# Fields that belong in the version history review entry
# (essentially all the review fields from the CSV)
SKIP_FIELDS = {'_quote_validation', '_title_mismatch_warning'}

def rebuild():
    print("=" * 60)
    print("REBUILDING review_version_history.json FROM DATABASE")
    print("=" * 60)

    # Load database
    print(f"\nLoading {DATABASE_CSV}...")
    papers = {}
    row_count = 0

    with open(DATABASE_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_count += 1
            filename = row.get('FILENAME', '')
            if not filename:
                continue

            # Build the review entry from CSV fields
            review = {}
            for key, value in row.items():
                if key in SKIP_FIELDS:
                    continue
                # Try to parse JSON-like fields (lists, dicts stored as strings)
                if value and value.startswith('['):
                    try:
                        review[key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        review[key] = value
                elif value and value.startswith('{'):
                    try:
                        review[key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        review[key] = value
                else:
                    review[key] = value

            # Use REVIEW_TIMESTAMP if available, else current time
            timestamp = row.get('REVIEW_TIMESTAMP', datetime.now().isoformat())

            # Build version entry
            version_entry = {
                "timestamp": timestamp,
                "review": review
            }

            # If paper already exists, append (handles duplicates in CSV)
            if filename in papers:
                # Check if this is truly a new version (different timestamp)
                existing_timestamps = {e['timestamp'] for e in papers[filename]}
                if timestamp not in existing_timestamps:
                    papers[filename].append(version_entry)
            else:
                papers[filename] = [version_entry]

    print(f"  ✅ Loaded {row_count} rows from CSV")
    print(f"  ✅ {len(papers)} unique papers")
    total_versions = sum(len(v) for v in papers.values())
    print(f"  ✅ {total_versions} total version entries")

    # Validate
    print(f"\nValidating rebuilt JSON...")
    rebuilt_json = json.dumps(papers, indent=2, default=str)
    # Verify it parses back
    json.loads(rebuilt_json)
    size_mb = len(rebuilt_json) / 1024 / 1024
    print(f"  ✅ Valid JSON ({size_mb:.1f} MB)")

    # Write
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(rebuilt_json)

    print(f"  💾 Saved to: {OUTPUT_FILE}")

    # Stats comparison
    corrupted_size = os.path.getsize(CORRUPTED_FILE) / 1024 / 1024
    rebuilt_size = os.path.getsize(OUTPUT_FILE) / 1024 / 1024

    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")
    print(f"  Corrupted file: {corrupted_size:.1f} MB (38K+ entries, corrupted)")
    print(f"  Rebuilt file:   {rebuilt_size:.1f} MB ({len(papers)} papers, {total_versions} versions)")
    print(f"  Size reduction: {(1 - rebuilt_size/corrupted_size)*100:.0f}%")
    print(f"\n  To apply:")
    print(f"    1. Backup: copy review_version_history.json review_version_history_CORRUPTED_BACKUP.json")
    print(f"    2. Replace: copy {OUTPUT_FILE} review_version_history.json")


if __name__ == '__main__':
    rebuild()
