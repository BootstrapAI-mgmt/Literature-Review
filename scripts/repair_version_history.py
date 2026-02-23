"""
Diagnostic and Repair Script for review_version_history.json

Strategy:
1. Binary-search the corrupted file to find ALL corruption boundaries
2. Compare valid sections against the backup to identify new content
3. Compare against the database CSV to verify completeness
4. Attempt surgical repair or recommend rebuild
"""

import json
import csv
import os
import sys
import time
from pathlib import Path

CORRUPTED_FILE = "review_version_history.json"
BACKUP_DIR = r"C:\Users\jpcol\OneDrive\Documents\Doctorate\Research\backups\neuromorphic-research_database-FEB2026-backup"
BACKUP_HISTORY = os.path.join(BACKUP_DIR, "review_version_history-FEB2026-backup.json")
BACKUP_HISTORY_ALT = os.path.join(BACKUP_DIR, "review_version_history.json") 
DATABASE_CSV = "neuromorphic-research_database.csv"
REPAIRED_FILE = "review_version_history_REPAIRED.json"

def get_file_size(path):
    return os.path.getsize(path)

def try_parse_json_bytes(data: bytes) -> tuple:
    """Try to parse JSON from bytes. Returns (success, data_or_error)."""
    try:
        parsed = json.loads(data.decode('utf-8'))
        return True, parsed
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, str(e)

def find_corruption_point_binary(filepath: str) -> int:
    """Binary search for the first byte where JSON parsing fails."""
    file_size = get_file_size(filepath)
    print(f"\n{'='*60}")
    print(f"PHASE 1: Binary search for corruption boundary")
    print(f"{'='*60}")
    print(f"File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
    
    # We know it fails at the full file. Find where it starts failing.
    # Strategy: try parsing up to various points, looking for valid JSON
    # by closing any open structures.
    
    lo, hi = 0, file_size
    last_good = 0
    
    with open(filepath, 'rb') as f:
        # First: try to find a point where we have at least one complete
        # top-level entry. Read in 1MB chunks and look for the pattern
        # of a complete JSON object boundary.
        
        # Read the whole file
        print("Reading file into memory...")
        f.seek(0)
        raw = f.read()
    
    print(f"File loaded. Searching for corruption...")
    
    # Strategy: we know the file is a JSON object { "key": [...], "key": [...], ... }
    # Find positions of top-level key boundaries (pattern: ], "filename.pdf": [)
    # Each boundary is a safe cut point where we can close the JSON.
    
    import re
    # Find all positions matching the pattern of a new top-level entry
    # Pattern: ],\n  "some_filename": [\n
    boundary_pattern = re.compile(rb'\],\s*\n\s*"[^"]+"\s*:\s*\[')
    boundaries = []
    for m in boundary_pattern.finditer(raw):
        boundaries.append(m.start() + 1)  # Position right after the ]
    
    print(f"Found {len(boundaries)} top-level entry boundaries")
    
    if not boundaries:
        print("ERROR: Could not find any top-level boundaries!")
        return -1
    
    # Binary search on the boundaries list
    lo, hi = 0, len(boundaries) - 1
    last_good_boundary = 0
    iterations = 0
    
    while lo <= hi:
        mid = (lo + hi) // 2
        cut_pos = boundaries[mid]
        
        # Try to parse: take everything up to this boundary, close the JSON
        test_data = raw[:cut_pos] + b'\n}'
        success, result = try_parse_json_bytes(test_data)
        
        iterations += 1
        if iterations % 5 == 0:
            print(f"  Binary search iteration {iterations}: boundary {mid}/{len(boundaries)}, "
                  f"pos {cut_pos:,} ({cut_pos/len(raw)*100:.1f}%): {'OK' if success else 'FAIL'}")
        
        if success:
            last_good_boundary = mid
            lo = mid + 1
        else:
            hi = mid - 1
    
    if last_good_boundary == 0 and not try_parse_json_bytes(raw[:boundaries[0]] + b'\n}')[0]:
        print("ERROR: Even the first entry is corrupted!")
        return -1
    
    good_pos = boundaries[last_good_boundary]
    print(f"\n✅ Last valid boundary: entry #{last_good_boundary} at byte {good_pos:,} "
          f"({good_pos/len(raw)*100:.1f}% of file)")
    
    # Now check if there's MORE valid content after the corruption
    print(f"\n{'='*60}")
    print(f"PHASE 2: Scanning for recoverable content after corruption")
    print(f"{'='*60}")
    
    recoverable_sections = []
    first_bad = last_good_boundary + 1
    
    if first_bad < len(boundaries):
        # Check each remaining boundary to see if sections after corruption are valid
        # Use a forward scan with jumps
        i = first_bad
        section_start = None
        
        while i < len(boundaries) - 1:
            start_pos = boundaries[i]
            end_pos = boundaries[i + 1] if i + 1 < len(boundaries) else len(raw) - 1
            
            # Extract just this one entry and try to parse it as {"key": [...]}
            # Find the key name
            key_match = re.search(rb'"([^"]+)"\s*:\s*\[', raw[start_pos:start_pos+500])
            if key_match:
                entry_data = b'{' + raw[start_pos + 1:end_pos] + b'\n}'
                # Try to see if this single entry is valid
                success, _ = try_parse_json_bytes(entry_data)
                if success:
                    if section_start is None:
                        section_start = i
                else:
                    if section_start is not None:
                        recoverable_sections.append((section_start, i - 1))
                        section_start = None
            i += 1
        
        if section_start is not None:
            recoverable_sections.append((section_start, len(boundaries) - 1))
    
    if recoverable_sections:
        print(f"Found {len(recoverable_sections)} recoverable section(s) after corruption:")
        for start_idx, end_idx in recoverable_sections:
            print(f"  Entries {start_idx}-{end_idx} "
                  f"(bytes {boundaries[start_idx]:,}-{boundaries[end_idx]:,})")
    else:
        print("No additional recoverable sections found after corruption point.")
    
    return good_pos, last_good_boundary, boundaries, raw, recoverable_sections


def analyze_and_repair():
    print("=" * 60)
    print("REVIEW VERSION HISTORY REPAIR TOOL")
    print("=" * 60)
    
    # --- Step 0: Load backup ---
    print(f"\nLoading backup from: {BACKUP_HISTORY}")
    backup_data = None
    for bp in [BACKUP_HISTORY, BACKUP_HISTORY_ALT]:
        if os.path.exists(bp):
            try:
                with open(bp, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                print(f"  ✅ Backup loaded: {len(backup_data)} papers, "
                      f"{sum(len(v) for v in backup_data.values())} total versions")
                break
            except Exception as e:
                print(f"  ❌ Failed to load {bp}: {e}")
    
    if not backup_data:
        print("  ⚠️ No valid backup found. Proceeding without backup comparison.")
    
    # --- Step 1: Load database CSV ---
    print(f"\nLoading database CSV: {DATABASE_CSV}")
    db_papers = set()
    try:
        with open(DATABASE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fn = row.get('FILENAME', '')
                if fn:
                    db_papers.add(fn)
        print(f"  ✅ Database has {len(db_papers)} unique papers")
    except Exception as e:
        print(f"  ❌ Failed to load database: {e}")
    
    # --- Step 2: Binary search for corruption ---
    result = find_corruption_point_binary(CORRUPTED_FILE)
    if result == -1:
        print("\n❌ FATAL: Could not find any valid content. Recommend full rebuild.")
        return
    
    good_pos, last_good_idx, boundaries, raw, recoverable = result
    
    # --- Step 3: Extract valid content ---
    print(f"\n{'='*60}")
    print("PHASE 3: Extracting and validating content")
    print(f"{'='*60}")
    
    # Parse the valid portion
    valid_data = raw[:good_pos] + b'\n}'
    success, parsed_valid = try_parse_json_bytes(valid_data)
    
    if not success:
        print(f"❌ Failed to parse valid portion: {parsed_valid}")
        return
    
    valid_papers = set(parsed_valid.keys())
    valid_versions = sum(len(v) for v in parsed_valid.values())
    print(f"  ✅ Valid portion: {len(valid_papers)} papers, {valid_versions} versions")
    
    # Try to recover content from after corruption
    recovered_data = {}
    if recoverable:
        for start_idx, end_idx in recoverable:
            for i in range(start_idx, min(end_idx + 1, len(boundaries))):
                start_pos = boundaries[i]
                end_pos = boundaries[i + 1] if i + 1 < len(boundaries) else len(raw) - 1
                
                key_match = re.search(rb'"([^"]+)"\s*:\s*\[', raw[start_pos:start_pos + 500])
                if key_match:
                    key = key_match.group(1).decode('utf-8')
                    entry_data = b'{' + raw[start_pos + 1:end_pos] + b'\n}'
                    success, entry_parsed = try_parse_json_bytes(entry_data)
                    if success:
                        recovered_data[key] = entry_parsed[key]
        
        print(f"  ✅ Recovered {len(recovered_data)} additional papers from after corruption")
    
    # --- Step 4: Compare against backup and database ---
    print(f"\n{'='*60}")
    print("PHASE 4: Comparison and gap analysis")
    print(f"{'='*60}")
    
    all_recovered = set(parsed_valid.keys()) | set(recovered_data.keys())
    
    # Papers in database but not in recovered version history
    if db_papers:
        missing_from_history = db_papers - all_recovered
        print(f"\n  Database papers: {len(db_papers)}")
        print(f"  Recovered history papers: {len(all_recovered)}")
        print(f"  Papers in DB missing from recovered history: {len(missing_from_history)}")
        if missing_from_history and len(missing_from_history) <= 20:
            for p in sorted(missing_from_history):
                print(f"    - {p}")
    
    if backup_data:
        backup_papers = set(backup_data.keys())
        new_papers = all_recovered - backup_papers
        lost_papers = backup_papers - all_recovered
        print(f"\n  Backup papers: {len(backup_papers)}")
        print(f"  New papers (not in backup): {len(new_papers)}")
        print(f"  Lost papers (in backup but not recovered): {len(lost_papers)}")
        
        if lost_papers:
            print(f"  ⚠️ These papers from the backup would need to be merged back:")
            for p in sorted(lost_papers)[:20]:
                print(f"    - {p}")
    
    # --- Step 5: Build repaired file ---
    print(f"\n{'='*60}")
    print("PHASE 5: Building repaired file")
    print(f"{'='*60}")
    
    repaired = dict(parsed_valid)
    
    # Merge recovered data
    for key, versions in recovered_data.items():
        if key in repaired:
            # Deduplicate by checking timestamps
            existing_timestamps = {v.get('timestamp', '') for v in repaired[key]}
            for v in versions:
                if v.get('timestamp', '') not in existing_timestamps:
                    repaired[key].append(v)
        else:
            repaired[key] = versions
    
    # Merge any lost papers from backup
    if backup_data:
        for key, versions in backup_data.items():
            if key not in repaired:
                repaired[key] = versions
    
    repaired_versions = sum(len(v) for v in repaired.values())
    print(f"  Repaired file will have {len(repaired)} papers, {repaired_versions} versions")
    
    # Validate the final result can be JSON-serialized
    try:
        repaired_json = json.dumps(repaired, indent=2, default=str)
        print(f"  ✅ Repaired JSON is valid ({len(repaired_json)/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"  ❌ Repaired JSON serialization failed: {e}")
        return
    
    # Final coverage check
    if db_papers:
        final_coverage = db_papers & set(repaired.keys())
        print(f"\n  Final coverage: {len(final_coverage)}/{len(db_papers)} "
              f"database papers have version history ({len(final_coverage)/len(db_papers)*100:.1f}%)")
        still_missing = db_papers - set(repaired.keys())
        if still_missing:
            print(f"  ⚠️ Still missing {len(still_missing)} papers (these are new entries "
                  f"with no version history yet):")
            for p in sorted(still_missing)[:10]:
                print(f"    - {p}")
    
    # Write repaired file
    with open(REPAIRED_FILE, 'w', encoding='utf-8') as f:
        f.write(repaired_json)
    
    repaired_size = os.path.getsize(REPAIRED_FILE) / 1024 / 1024
    print(f"\n  💾 Repaired file saved to: {REPAIRED_FILE} ({repaired_size:.1f} MB)")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Original file:  192.3 MB (corrupted)")
    print(f"  Backup file:    {get_file_size(BACKUP_HISTORY)/1024/1024:.1f} MB")
    print(f"  Repaired file:  {repaired_size:.1f} MB")
    print(f"  Papers:         {len(repaired)}")
    print(f"  Versions:       {repaired_versions}")
    if db_papers:
        print(f"  DB coverage:    {len(final_coverage)}/{len(db_papers)} "
              f"({len(final_coverage)/len(db_papers)*100:.1f}%)")
    print(f"\n  To apply: copy {REPAIRED_FILE} over {CORRUPTED_FILE}")
    print(f"  Command: copy-item {REPAIRED_FILE} {CORRUPTED_FILE} -Force")


if __name__ == '__main__':
    import re
    analyze_and_repair()
