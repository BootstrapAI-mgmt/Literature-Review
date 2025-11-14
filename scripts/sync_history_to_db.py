"""
Database Sync Utility
Version: 2.2 (Full Cell-by-Cell Sync with Evidence Quality Scores)
Date: 2025-11-14

This script performs a full synchronization from the 'review_version_history.json'
(the "source of truth") to the 'neuromorphic-research_database.csv'.

It uses a master column order list to ensure the output CSV's headers
are in the exact order specified by the "REVIEWER ORDER".

Version 2.2 adds support for evidence quality scores and provenance metadata:
- Extracts multi-dimensional quality scores (strength, rigor, relevance, etc.)
- Syncs provenance metadata (page numbers, sections)
- Maintains backward compatibility with legacy claims without quality scores
"""

import os
import sys
import json
import csv
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = 'neuromorphic-research_database.csv'
VERSION_HISTORY_FILE = 'review_version_history.json'


# --- Logging Setup ---
class UTF8Formatter(logging.Formatter):
    """Custom formatter that handles Unicode properly on Windows"""
    def format(self, record):
        if hasattr(record, 'msg'): record.msg = str(record.msg)
        try: return super().format(record)
        except UnicodeEncodeError:
            record.msg = record.msg.encode('utf-8', 'replace').decode('utf-8')
            return super().format(record)

log_handlers = []
file_handler = logging.FileHandler('db_sync.log', encoding='utf-8')
file_handler.setFormatter(UTF8Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_handlers.append(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(UTF8Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_handlers.append(console_handler)
logging.basicConfig(level=logging.INFO, handlers=log_handlers)
logger = logging.getLogger(__name__)

def safe_print(message):
    """Print message safely handling Unicode on Windows"""
    try: print(message)
    except UnicodeEncodeError:
        print(str(message).encode(sys.stdout.encoding or 'utf-8', 'replace').decode(sys.stdout.encoding or 'utf-8'))


# --- Data Structure Definitions (from Journal-Reviewer v3.2) ---

class PaperAnalyzer:
    """Stub class to hold the master list of CSV headers in the correct order."""

    # --- THIS IS THE NEW MASTER COLUMN ORDER ---
    # This list is the new "source of truth" for column order.
    # 
    # Note: Evidence quality scores and provenance metadata are embedded within
    # the 'Requirement(s)' column as JSON. Each claim in the Requirements array
    # may contain the following additional fields (if available):
    #   Quality Scores:
    #     - EVIDENCE_COMPOSITE_SCORE, EVIDENCE_STRENGTH_SCORE, EVIDENCE_RIGOR_SCORE
    #     - EVIDENCE_RELEVANCE_SCORE, EVIDENCE_DIRECTNESS, EVIDENCE_IS_RECENT
    #     - EVIDENCE_REPRODUCIBILITY_SCORE, STUDY_TYPE, CONFIDENCE_LEVEL
    #   Provenance:
    #     - PROVENANCE_PAGE_NUMBERS (JSON array), PROVENANCE_SECTION, PROVENANCE_QUOTE_PAGE
    #
    DATABASE_COLUMN_ORDER = [
        "ANALYSIS_GAPS", "APA_REFERENCE", "APPLICABILITY_NOTES", "BIOLOGICAL_FIDELITY",
        "BRAIN_REGIONS", "COMPUTATIONAL_COMPLEXITY", "CORE_CONCEPTS", "CORE_DOMAIN",
        "CORE_DOMAIN_RELEVANCE_SCORE", "CROSS_REFERENCES_COUNT", "DATASET_USED",
        "ENERGY_EFFICIENCY", "EXTRACTION_METHOD", "EXTRACTION_QUALITY", "FILENAME",
        "FULL_TEXT_LINK", "IMPLEMENTATION_DETAILS", "IMPROVEMENT_SUGGESTIONS",
        "INTERDISCIPLINARY_BRIDGES", "KEYWORDS", "MAJOR_FINDINGS", "MATURITY_LEVEL",
        "MENTIONED_PAPERS", "NETWORK_ARCHITECTURE", "PUBLICATION_YEAR",
        "REPRODUCIBILITY_SCORE", "REVIEW_TIMESTAMP", "RISKS", "Requirement(s)",
        "SCALABILITY_NOTES", "SIMILAR_PAPERS", "SOURCE",
        "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE", "SUB_DOMAIN",
        "SUMMARIZED_FROM_CHUNKS", "TITLE", "VALIDATION_METHOD"
    ]


# --- Core Functions ---

def load_existing_reviews_as_dict(csv_file=OUTPUT_CSV_FILE) -> Dict[str, Dict]:
    """Loads CSV into a dictionary keyed by FILENAME for fast lookup."""
    reviews_dict = {}
    if not os.path.exists(csv_file):
        logger.warning(f"CSV file not found at {csv_file}. A new file will be created.")
        return reviews_dict

    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
        df = df.replace({np.nan: None})  # Use None, not empty string
        reviews = df.to_dict('records')

        for review in reviews:
            filename = review.get('FILENAME')
            if filename:
                # Deserialize list-like columns for comparison
                for col in review:
                    if isinstance(review[col], str) and review[col].startswith('['):
                        try:
                            review[col] = json.loads(review[col].replace("'", "\""))
                        except json.JSONDecodeError:
                            pass  # Keep as string if it fails
                reviews_dict[filename] = review

        logger.info(f"Loaded and parsed {len(reviews)} existing reviews from {csv_file}")
        return reviews_dict
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file is empty: {csv_file}")
        return reviews_dict
    except Exception as e:
        logger.error(f"Could not load existing reviews from {csv_file}: {e}")
        return reviews_dict


def overwrite_csv_with_master_list(master_list: List[Dict], csv_file=OUTPUT_CSV_FILE):
    """
    Overwrites the target CSV with the provided master list,
    using the master column order.
    """
    if not master_list:
        logger.warning("Master list is empty. No data to write.")
        return

    try:
        # --- MODIFIED LOGIC ---
        # 1. Use the new explicit order as the base
        fieldnames = PaperAnalyzer.DATABASE_COLUMN_ORDER.copy()

        # 2. Find any *extra* keys in the data that are NOT in the defined order
        all_data_keys = set().union(*(d.keys() for d in master_list))
        extra_keys = sorted(list(all_data_keys - set(fieldnames)))

        # 3. Add extra keys to the end (for future-proofing)
        final_fieldnames = fieldnames + extra_keys

        if extra_keys:
            logger.warning(f"Found {len(extra_keys)} keys in data not in standard column order. Appending to end: {extra_keys}")
        # --- END MODIFIED LOGIC ---

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=final_fieldnames, restval='', extrasaction='ignore', quoting=csv.QUOTE_ALL)
            writer.writeheader()

            for review in master_list:
                row_to_write = {}
                for key in final_fieldnames:
                    value = review.get(key)
                    # Serialize lists/dicts to JSON strings
                    if isinstance(value, list) or isinstance(value, dict):
                        row_to_write[key] = json.dumps(value)
                    elif value is None:
                        row_to_write[key] = ''
                    else:
                        row_to_write[key] = value
                writer.writerow(row_to_write)

        logger.info(f"Successfully overwrote {csv_file} with {len(master_list)} synced reviews.")
        safe_print(f"💾 Successfully synced {len(master_list)} reviews to {csv_file} with correct column order.")
    except PermissionError:
        logger.error(f"PERMISSION ERROR: Could not write to {csv_file}. Is the file open in Excel?")
        safe_print(f"❌ PERMISSION ERROR: Could not write to {csv_file}. Please close it and try again.")
    except Exception as e:
        logger.error(f"Error saving to CSV {csv_file}: {e}")
        safe_print(f"❌ Error saving to CSV {csv_file}: {e}")


def extract_quality_scores_from_claim(claim: Dict) -> Dict:
    """
    Extract evidence quality scores and provenance metadata for CSV columns.
    
    This function enriches claims with quality score fields to ensure they
    are properly synced to the CSV database. It handles backward compatibility
    by setting None for missing quality data.
    
    Args:
        claim: Claim dictionary with optional evidence_quality and provenance fields
    
    Returns:
        Dictionary with quality score and provenance columns (modifies claim in-place)
    """
    quality = claim.get('evidence_quality', {})
    provenance = claim.get('provenance', {})
    
    # Extract quality scores (None if not present for backward compatibility)
    quality_fields = {
        'EVIDENCE_COMPOSITE_SCORE': quality.get('composite_score'),
        'EVIDENCE_STRENGTH_SCORE': quality.get('strength_score'),
        'EVIDENCE_RIGOR_SCORE': quality.get('rigor_score'),
        'EVIDENCE_RELEVANCE_SCORE': quality.get('relevance_score'),
        'EVIDENCE_DIRECTNESS': quality.get('directness'),
        'EVIDENCE_IS_RECENT': quality.get('is_recent'),
        'EVIDENCE_REPRODUCIBILITY_SCORE': quality.get('reproducibility_score'),
        'STUDY_TYPE': quality.get('study_type'),
        'CONFIDENCE_LEVEL': quality.get('confidence_level')
    }
    
    # Extract provenance metadata
    page_numbers = provenance.get('page_numbers')
    provenance_fields = {
        'PROVENANCE_PAGE_NUMBERS': json.dumps(page_numbers) if page_numbers else None,
        'PROVENANCE_SECTION': provenance.get('section'),
        'PROVENANCE_QUOTE_PAGE': provenance.get('quote_page')
    }
    
    # Add fields to claim
    claim.update(quality_fields)
    claim.update(provenance_fields)
    
    return claim


def enrich_claims_with_quality_scores(review: Dict) -> Dict:
    """
    Enrich all claims in a review with quality scores and provenance metadata.
    
    This ensures that when claims are synced to CSV, they include all quality
    score dimensions and provenance information needed for gap analysis.
    
    Args:
        review: Review dictionary containing 'Requirement(s)' list
    
    Returns:
        Review dictionary with enriched claims
    """
    requirements = review.get('Requirement(s)', [])
    
    if isinstance(requirements, list):
        for claim in requirements:
            if isinstance(claim, dict):
                extract_quality_scores_from_claim(claim)
    
    return review


def load_version_history() -> Optional[Dict]:
    """Loads the complete review history from the JSON file."""
    if not os.path.exists(VERSION_HISTORY_FILE):
        logger.error(f"History file not found: {VERSION_HISTORY_FILE}")
        safe_print(f"❌ History file not found: {VERSION_HISTORY_FILE}")
        return None
    try:
        with open(VERSION_HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        logger.info(f"Loaded history for {len(history)} files from {VERSION_HISTORY_FILE}")
        return history
    except Exception as e:
        logger.error(f"Failed to load or parse {VERSION_HISTORY_FILE}: {e}")
        safe_print(f"❌ Failed to load or parse {VERSION_HISTORY_FILE}: {e}")
        return None


def main():
    """Main sync function"""
    logger.info("\n" + "=" * 80)
    logger.info("DATABASE SYNC UTILITY v2.2 (Full Sync, Column Order & Quality Scores)")
    logger.info("=" * 80)

    # 1. Load the history file (source of truth)
    history = load_version_history()
    if not history:
        logger.error("Could not load history file. Exiting.")
        return

    # 2. Load the existing CSV (to find orphans and compare)
    safe_print(f"Loading existing database: {OUTPUT_CSV_FILE}...")
    csv_reviews_dict = load_existing_reviews_as_dict(OUTPUT_CSV_FILE)
    csv_filenames = set(csv_reviews_dict.keys())

    master_review_list = []
    history_filenames = set(history.keys())
    files_to_update = 0
    files_added = 0
    files_preserved = 0

    safe_print("Comparing history (source of truth) with CSV (current state)...")

    # 3. Iterate through history and build the master list
    for filename, versions in history.items():
        if not versions:
            logger.warning(f"No versions found for {filename} in history. Skipping.")
            continue

        latest_review = versions[-1].get('review')
        if not latest_review:
            logger.warning(f"No 'review' key in last version for {filename}. Skipping.")
            continue

        # Ensure FILENAME key is set
        latest_review['FILENAME'] = filename
        
        # Enrich claims with quality scores and provenance metadata
        latest_review = enrich_claims_with_quality_scores(latest_review)

        if filename not in csv_filenames:
            # File is missing from CSV entirely
            logger.info(f"Adding new file to sync list: {filename}")
            files_added += 1
            master_review_list.append(latest_review)
        else:
            # File exists, compare cell by cell
            csv_review = csv_reviews_dict[filename]

            # Simple check: compare JSON representations.
            latest_review_serialized = {}
            for key, value in latest_review.items():
                if isinstance(value, list) or isinstance(value, dict):
                    latest_review_serialized[key] = json.dumps(value)
                else:
                    latest_review_serialized[key] = value

            csv_review_serialized = {}
            for key, value in csv_review.items():
                if isinstance(value, list) or isinstance(value, dict):
                    csv_review_serialized[key] = json.dumps(value)
                else:
                    csv_review_serialized[key] = value

            # Check if all keys from history are in CSV and match
            is_different = False
            for key, history_val in latest_review_serialized.items():
                csv_val = csv_review_serialized.get(key)
                # Handle None/""/[] equivalence
                if (history_val is None or history_val == "" or history_val == "[]") and (csv_val is None or csv_val == "" or csv_val == "[]"):
                    continue
                if history_val != csv_val:
                    is_different = True
                    logger.warning(f"Difference found for {filename} in column '{key}'.")
                    logger.debug(f"  History: {str(history_val)[:100]}...")
                    logger.debug(f"  CSV:     {str(csv_val)[:100]}...")
                    break

            if is_different:
                logger.info(f"Updating stale file in sync list: {filename}")
                files_to_update += 1
                master_review_list.append(latest_review) # Add the *correct* version
            else:
                # They are identical, add the CSV version (preserves column order)
                master_review_list.append(csv_review)

    # 4. Check for "orphan" files (in CSV but not history)
    orphan_filenames = csv_filenames - history_filenames
    for filename in orphan_filenames:
        logger.warning(f"Preserving orphan file (in CSV, not history): {filename}")
        files_preserved += 1
        master_review_list.append(csv_reviews_dict[filename])

    # 5. Overwrite the CSV with the new master list
    if files_added > 0 or files_to_update > 0 or orphan_filenames:
        if orphan_filenames:
             safe_print(f"Warning: {len(orphan_filenames)} orphan files found in CSV. Re-writing file to maintain them.")
        safe_print(f"Sync required: {files_added} new files, {files_to_update} updated files.")
        safe_print(f"Overwriting {OUTPUT_CSV_FILE} with complete, synced data...")
        overwrite_csv_with_master_list(master_review_list, OUTPUT_CSV_FILE)
    else:
        logger.info("Database is already up-to-date. No changes needed.")
        safe_print("✅ Database is already up-to-date. Nothing to sync.")

    if files_preserved > 0:
        safe_print(f"Note: {files_preserved} orphan files were found in the CSV and preserved.")
        logger.warning(f"Preserved {files_preserved} orphan files not found in history.")

    logger.info("=" * 80)


if __name__ == "__main__":
    main()