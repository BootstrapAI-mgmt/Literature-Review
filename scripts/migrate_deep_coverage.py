#!/usr/bin/env python3
"""
Deep Coverage Database Migration Script
Version: 1.0
Date: 2025-11-10

This script migrates data from deep_coverage_database.json (deprecated)
to review_version_history.json (source of truth).

This is part of implementing Task Card #4: Design Decision - Deep Coverage Database
Decision: Option A - Merge into Version History

Usage:
    python migrate_deep_coverage.py

The script will:
1. Load existing deep_coverage_database.json (if exists)
2. Load review_version_history.json
3. Merge deep coverage claims into the appropriate paper's Requirement(s) list
4. Back up the original files
5. Write updated version history
6. Create a deprecation notice for deep_coverage_database.json
"""

import os
import sys
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional

# --- CONFIGURATION ---
DEEP_COVERAGE_DB_FILE = 'deep_coverage_database.json'
VERSION_HISTORY_FILE = 'review_version_history.json'
BACKUP_SUFFIX = '.backup_before_migration'

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_json_file(filepath: str) -> Optional[Dict | List]:
    """Load a JSON file with error handling."""
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {filepath}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def save_json_file(filepath: str, data: Dict | List, indent: int = 2):
    """Save data to JSON file with error handling."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        logger.info(f"Successfully saved {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False


def backup_file(filepath: str) -> bool:
    """Create a backup of a file."""
    if not os.path.exists(filepath):
        logger.info(f"No file to backup: {filepath}")
        return True
    
    backup_path = filepath + BACKUP_SUFFIX
    try:
        shutil.copy2(filepath, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup of {filepath}: {e}")
        return False


def convert_deep_coverage_to_requirement(deep_claim: Dict, timestamp: str) -> Dict:
    """
    Convert a deep coverage entry to version history requirement format.
    
    Deep Coverage Entry fields:
        - claim_id, filename, pillar, requirement_key, sub_requirement_key,
          claim_summary, evidence_chunk, page_number, status, reviewer_confidence,
          judge_notes, review_timestamp
    
    Version History Requirement fields (extended):
        - claim_id, pillar, sub_requirement, evidence_chunk, claim_summary, status
        - Added: requirement_key, page_number, reviewer_confidence, judge_notes, 
                 review_timestamp, source
    """
    return {
        "claim_id": deep_claim.get("claim_id", ""),
        "pillar": deep_claim.get("pillar", ""),
        "sub_requirement": deep_claim.get("sub_requirement_key", ""),
        "evidence_chunk": deep_claim.get("evidence_chunk", ""),
        "claim_summary": deep_claim.get("claim_summary", ""),
        "status": deep_claim.get("status", "pending_judge_review"),
        # Extended fields from deep coverage
        "requirement_key": deep_claim.get("requirement_key", ""),
        "page_number": deep_claim.get("page_number", 0),
        "reviewer_confidence": deep_claim.get("reviewer_confidence", 0.0),
        "judge_notes": deep_claim.get("judge_notes", ""),
        "review_timestamp": deep_claim.get("review_timestamp", timestamp),
        "source": "deep_reviewer"  # Mark where this claim came from
    }


def migrate_deep_coverage_to_version_history(
    deep_coverage_data: List[Dict],
    version_history: Dict
) -> tuple[Dict, int, int]:
    """
    Migrate deep coverage claims into version history.
    
    Returns:
        (updated_version_history, claims_added, claims_skipped)
    """
    claims_added = 0
    claims_skipped = 0
    migration_timestamp = datetime.now().isoformat()
    
    # Group deep coverage claims by filename
    claims_by_file = {}
    for claim in deep_coverage_data:
        filename = claim.get("filename")
        if not filename:
            logger.warning(f"Skipping claim without filename: {claim.get('claim_id', 'unknown')}")
            claims_skipped += 1
            continue
        
        if filename not in claims_by_file:
            claims_by_file[filename] = []
        claims_by_file[filename].append(claim)
    
    logger.info(f"Found claims for {len(claims_by_file)} files in deep coverage database")
    
    # For each file with deep coverage claims
    for filename, file_claims in claims_by_file.items():
        logger.info(f"Processing {len(file_claims)} claims for {filename}")
        
        # Check if file exists in version history
        if filename not in version_history:
            logger.warning(f"File {filename} not found in version history. Creating new entry.")
            version_history[filename] = []
        
        # Get or create latest version
        if not version_history[filename]:
            # Create new version entry
            version_history[filename].append({
                "timestamp": migration_timestamp,
                "review": {
                    "FILENAME": filename,
                    "Requirement(s)": []
                },
                "changes": {
                    "status": "deep_coverage_migration"
                }
            })
            latest_version = version_history[filename][0]
        else:
            latest_version = version_history[filename][-1]
        
        # Ensure review has Requirement(s) field
        if "Requirement(s)" not in latest_version["review"]:
            latest_version["review"]["Requirement(s)"] = []
        
        # Get existing claim IDs to avoid duplicates
        existing_claim_ids = {
            req.get("claim_id") 
            for req in latest_version["review"]["Requirement(s)"]
            if "claim_id" in req
        }
        
        # Add deep coverage claims
        for deep_claim in file_claims:
            claim_id = deep_claim.get("claim_id")
            
            if claim_id in existing_claim_ids:
                logger.debug(f"Skipping duplicate claim {claim_id} for {filename}")
                claims_skipped += 1
                continue
            
            # Convert and add the claim
            requirement = convert_deep_coverage_to_requirement(
                deep_claim, 
                migration_timestamp
            )
            latest_version["review"]["Requirement(s)"].append(requirement)
            existing_claim_ids.add(claim_id)
            claims_added += 1
            logger.debug(f"Added claim {claim_id} to {filename}")
    
    return version_history, claims_added, claims_skipped


def create_deprecation_notice():
    """Create a deprecation notice for deep_coverage_database.json."""
    notice = {
        "DEPRECATED": True,
        "deprecation_date": datetime.now().isoformat(),
        "migration_status": "completed",
        "message": (
            "This file is DEPRECATED as of 2025-11-10. "
            "All deep coverage claims are now stored in review_version_history.json. "
            "This file is kept for historical reference only. "
            "See migrate_deep_coverage.py for migration details."
        ),
        "new_location": "review_version_history.json",
        "task_card": "Task Card #4: Design Decision - Deep Coverage Database",
        "decision": "Option A: Merge into Version History"
    }
    
    notice_file = 'deep_coverage_database.DEPRECATED.json'
    if save_json_file(notice_file, notice):
        logger.info(f"Created deprecation notice: {notice_file}")
        return True
    return False


def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("DEEP COVERAGE DATABASE MIGRATION")
    logger.info("Task Card #4: Design Decision - Deep Coverage Database")
    logger.info("Decision: Option A - Merge into Version History")
    logger.info("=" * 80)
    
    # 1. Load deep coverage database
    logger.info("\n=== Step 1: Load Deep Coverage Database ===")
    deep_coverage_data = load_json_file(DEEP_COVERAGE_DB_FILE)
    
    if not deep_coverage_data:
        logger.info("No deep coverage database found. Nothing to migrate.")
        logger.info("Creating deprecation notice for future reference...")
        create_deprecation_notice()
        logger.info("\n✅ Migration complete (no data to migrate)")
        return
    
    if not isinstance(deep_coverage_data, list):
        logger.error("Deep coverage database is not a list. Cannot migrate.")
        return
    
    logger.info(f"Found {len(deep_coverage_data)} claims in deep coverage database")
    
    # 2. Load version history
    logger.info("\n=== Step 2: Load Version History ===")
    version_history = load_json_file(VERSION_HISTORY_FILE)
    
    if not version_history:
        logger.error(f"Version history file not found: {VERSION_HISTORY_FILE}")
        logger.error("Cannot proceed with migration without version history.")
        return
    
    if not isinstance(version_history, dict):
        logger.error("Version history is not a dictionary. Cannot migrate.")
        return
    
    logger.info(f"Version history contains {len(version_history)} files")
    
    # 3. Create backups
    logger.info("\n=== Step 3: Create Backups ===")
    if not backup_file(DEEP_COVERAGE_DB_FILE):
        logger.error("Failed to backup deep coverage database. Aborting.")
        return
    
    if not backup_file(VERSION_HISTORY_FILE):
        logger.error("Failed to backup version history. Aborting.")
        return
    
    # 4. Perform migration
    logger.info("\n=== Step 4: Migrate Data ===")
    updated_history, claims_added, claims_skipped = migrate_deep_coverage_to_version_history(
        deep_coverage_data,
        version_history
    )
    
    logger.info(f"Migration complete: {claims_added} claims added, {claims_skipped} skipped")
    
    # 5. Save updated version history
    logger.info("\n=== Step 5: Save Updated Version History ===")
    if not save_json_file(VERSION_HISTORY_FILE, updated_history):
        logger.error("Failed to save updated version history. Check backups.")
        return
    
    # 6. Create deprecation notice
    logger.info("\n=== Step 6: Create Deprecation Notice ===")
    create_deprecation_notice()
    
    # 7. Summary
    logger.info("\n" + "=" * 80)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Deep coverage claims processed: {len(deep_coverage_data)}")
    logger.info(f"Claims added to version history: {claims_added}")
    logger.info(f"Claims skipped (duplicates): {claims_skipped}")
    logger.info(f"Version history files affected: {len([f for f in version_history if any(v['changes'].get('status') == 'deep_coverage_migration' for v in version_history[f])])}")
    logger.info("\nBackup files created:")
    logger.info(f"  - {DEEP_COVERAGE_DB_FILE}{BACKUP_SUFFIX}")
    logger.info(f"  - {VERSION_HISTORY_FILE}{BACKUP_SUFFIX}")
    logger.info("\nNext steps:")
    logger.info("  1. Review the updated version history")
    logger.info("  2. Run sync_history_to_db.py to update the CSV database")
    logger.info("  3. Update Deep-Reviewer.py to use version history")
    logger.info("  4. Update Judge.py to use version history")
    logger.info("  5. Test the updated system")
    logger.info("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    main()
