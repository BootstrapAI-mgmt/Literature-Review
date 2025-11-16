"""
Gap-Bridging Recommendation Engine
Version: 1.0
Date: 2025-11-01

This script reads the output from the Orchestrator (gap_analysis_report.json)
and the main database (neuromorphic-research_database.csv) to generate
novel search queries for filling identified research gaps.
"""

import os
import sys
import json
import csv
import time
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
# Use google.generativeai (legacy API) - note: actual API calls via APIManager
import google.generativeai as genai
from google.generativeai import types
from dotenv import load_dotenv
import logging
import pickle
from sentence_transformers import SentenceTransformer
import warnings
from literature_review.utils.api_manager import APIManager

from literature_review.utils.api_manager import APIManager

# --- CONFIGURATION & SETUP ---
# File paths
GAP_REPORT_FILE = 'gap_analysis_report.json'
RESEARCH_DB_FILE = 'data/processed/neuromorphic-research_database.csv'
OUTPUT_FILE = 'suggested_searches.md'
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'recommender_cache')

# Analysis configuration
RECOMMENDATION_CONFIG = {
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,
    'API_CALLS_PER_MINUTE': 10,  # Conservative limit for gemini-2.5-flash (1000 RPM available)
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recommendation_engine.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def safe_print(message):
    """Print message safely handling Unicode on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(str(message).encode(sys.stdout.encoding or 'utf-8', 'replace').decode(sys.stdout.encoding or 'utf-8'))


os.makedirs(CACHE_DIR, exist_ok=True)


# --- END APIManager CLASS ---


# --- PHASE 1: DATA LOADING ---

def load_inputs(gap_file: str, db_file: str) -> Tuple[Optional[Dict], Optional[pd.DataFrame]]:
    """Loads the gap analysis JSON and the research database CSV."""
    logger.info(f"Loading gap analysis report from: {gap_file}")
    gap_data = None
    if os.path.exists(gap_file):
        try:
            with open(gap_file, 'r', encoding='utf-8') as f:
                gap_data = json.load(f)
            logger.info("✅ Successfully loaded gap analysis report.")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error decoding JSON from {gap_file}: {e}")
        except Exception as e:
            logger.error(f"❌ Error reading {gap_file}: {e}")
    else:
        logger.error(f"❌ File not found: {gap_file}")

    logger.info(f"Loading research database from: {db_file}")
    db_dataframe = None
    if os.path.exists(db_file):
        try:
            db_dataframe = pd.read_csv(db_file)
            # Handle potential NaNs in keyword/concept columns
            for col in ['KEYWORDS', 'CORE_CONCEPTS']:
                if col in db_dataframe.columns:
                    db_dataframe[col] = db_dataframe[col].fillna('[]')
            logger.info(f"✅ Successfully loaded research database with {len(db_dataframe)} entries.")
        except pd.errors.ParserError as e:
            logger.critical(f"❌ CRITICAL: The CSV file {db_file} is corrupt. {e}")
            safe_print(
                f"❌ CRITICAL: The file '{db_file}' is corrupt. Please fix or delete it and re-run the orchestrator.")
        except Exception as e:
            logger.error(f"❌ Error reading {db_file}: {e}")
    else:
        logger.error(f"❌ File not found: {db_file}")

    return gap_data, db_dataframe


# --- PHASE 2: GAP IDENTIFICATION ---

def find_and_prioritize_gaps(gap_data: Dict, threshold: int = 80) -> List[Dict]:
    """Finds and prioritizes all sub-requirement gaps below a threshold."""
    logger.info(f"Finding all gaps with completeness < {threshold}%...")
    gaps = []
    for pillar_name, pillar_data in gap_data.items():
        for req_key, req_data in pillar_data.get('analysis', {}).items():
            for sub_req_key, sub_req_data in req_data.items():
                completeness = sub_req_data.get('completeness_percent', 100)
                if completeness < threshold:
                    gaps.append({
                        "pillar": pillar_name,
                        "requirement": req_key,
                        "sub_requirement": sub_req_key,
                        "completeness": completeness,
                        "gap_text": sub_req_data.get('gap_analysis', 'N/A'),
                        "evidence_papers": sub_req_data.get('evidence_papers', [])
                    })

    sorted_gaps = sorted(gaps, key=lambda x: x['completeness'])
    logger.info(f"✅ Found and prioritized {len(sorted_gaps)} gaps.")
    return sorted_gaps


# --- PHASE 3: EXISTING COVERAGE ANALYSIS ---

def parse_keyword_field(field_data: Any) -> set:
    """Safely parses a keyword/concept field that might be a list or a string."""
    if isinstance(field_data, list):
        return set(str(item) for item in field_data)
    if isinstance(field_data, str) and field_data.startswith('['):
        try:
            # Handle "['item1', 'item2']"
            return set(json.loads(field_data.replace("'", "\"")))
        except json.JSONDecodeError:
            # Handle "[item1, item2]"
            return set(item.strip() for item in field_data.strip("[]").split(','))
    return set()


def get_existing_keywords(evidence_papers: List[str], db_dataframe: pd.DataFrame) -> set:
    """Extracts all unique KEYWORDS and CORE_CONCEPTS from a list of papers."""
    if not evidence_papers:
        return set()

    relevant_rows = db_dataframe[db_dataframe['FILENAME'].isin(evidence_papers)]
    if relevant_rows.empty:
        return set()

    all_keywords = set()
    if 'KEYWORDS' in relevant_rows.columns:
        for keywords_data in relevant_rows['KEYWORDS']:
            all_keywords.update(parse_keyword_field(keywords_data))

    if 'CORE_CONCEPTS' in relevant_rows.columns:
        for concepts_data in relevant_rows['CORE_CONCEPTS']:
            all_keywords.update(parse_keyword_field(concepts_data))

    # Remove generic/useless keywords
    all_keywords.discard("N/A")
    all_keywords.discard("")
    return all_keywords


# --- PHASE 4: "BRIDGE" QUERY GENERATION ---

def generate_bridge_queries(gap_info: Dict, existing_keywords: set, api_manager: APIManager) -> List[str]:
    """Generates novel search queries to bridge a specific research gap."""

    if not existing_keywords:
        existing_keywords_str = "None. This is a completely unaddressed gap."
    else:
        existing_keywords_str = ", ".join(sorted(list(existing_keywords)))

    prompt = f"""
You are a PhD-level research assistant specializing in literature review for neuromorphic computing and neuroscience.

My goal is to find new papers that fill a specific research gap.

**The Research Pillar:**
{gap_info['pillar']}

**The Specific Gap:**
I need to find papers on: "{gap_info['sub_requirement']}"
My current analysis of this gap is: "{gap_info['gap_text']}"

**Existing Coverage (CRITICAL):**
I have already found papers using the following keywords. Your suggestions MUST AVOID simply repeating these terms and should find novel connections, synonyms, or related concepts.
Existing keywords to avoid:
{existing_keywords_str}

**Your Task:**
Generate 5 novel, precise, and creative search queries for an academic search engine (like Google Scholar or IEEE Xplore) that will find papers to fill this gap *without* overlapping with my existing keywords.

Return your answer as a clean JSON list of strings.
Example: ["query 1", "query 2", "query 3", "query 4", "query 5"]
"""

    try:
        queries = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)  # Always generate new queries
        if not queries or not isinstance(queries, list):
            logger.error(f"API returned invalid data for gap: {gap_info['sub_requirement']}")
            return ["Error: API returned invalid data."]

        # Ensure list contains only strings
        queries = [str(q) for q in queries if isinstance(q, str)]
        return queries

    except Exception as e:
        logger.error(f"API call failed for gap {gap_info['sub_requirement']}: {e}")
        return [f"Error during API call: {e}"]


# --- PHASE 5: MAIN ORCHESTRATION & REPORTING ---

def main():
    """Main execution function to generate the recommendation report."""
    start_time = time.time()
    logger.info("\n" + "=" * 80)
    logger.info("🚀 STARTING GAP-BRIDGING RECOMMENDATION ENGINE v1.0")
    logger.info("=" * 80)

    try:
        api_manager = APIManager()
    except Exception as e:
        logger.critical(f"❌ Failed to initialize APIManager. Exiting. Error: {e}")
        safe_print(f"❌ Failed to initialize APIManager. Exiting. Error: {e}")
        return

    gap_data, db_df = load_inputs(GAP_REPORT_FILE, RESEARCH_DB_FILE)

    if gap_data is None or db_df is None:
        logger.critical("❌ Failed to load input files. See errors above. Exiting.")
        safe_print("❌ Failed to load input files. See errors above. Exiting.")
        return

    gaps = find_and_prioritize_gaps(gap_data, threshold=ANALYSIS_CONFIG['COMPLETENESS_THRESHOLD'])

    if not gaps:
        logger.info("🎉 No gaps found below the {ANALYSIS_CONFIG['COMPLETENESS_THRESHOLD']}% threshold. Nothing to do.")
        safe_print("🎉 No gaps found. Your research coverage is excellent!")
        return

    report_content = [f"# Gap-Bridging Search Recommendations\n_Generated: {datetime.now().isoformat()}_\n"]

    for i, gap in enumerate(gaps, 1):
        pillar = gap['pillar'].split(':')[-1].strip()
        sub_req = gap['sub_requirement'].split(':')[-1].strip()

        logger.info(f"\n--- Processing Gap {i}/{len(gaps)}: {pillar} / {sub_req} ({gap['completeness']}%) ---")
        safe_print(f"\nProcessing Gap {i}/{len(gaps)}: {sub_req} ({gap['completeness']}%)")

        existing_keywords = get_existing_keywords(gap['evidence_papers'], db_df)
        logger.info(f"   Found {len(existing_keywords)} existing keywords/concepts to avoid.")

        new_queries = generate_bridge_queries(gap, existing_keywords, api_manager)
        logger.info("   Generated new queries.")

        # Format for Markdown report
        report_content.append(f"## {i}. Pillar: {pillar}")
        report_content.append(f"### 🎯 Gap: {sub_req}")
        report_content.append(f"* **Current Completeness:** {gap['completeness']}%")
        report_content.append(f"* **Orchestrator Analysis:** \"{gap['gap_text']}\"")
        if existing_keywords:
            report_content.append(
                f"* **Existing Keywords (Avoid These):** `{', '.join(sorted(list(existing_keywords)))}`")
        report_content.append("\n")

        report_content.append("### 💡 Suggested New Search Queries:")
        for q in new_queries:
            report_content.append(f"1.  `{q}`")
        report_content.append("\n---")

    # Write the final report
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_content))
        logger.info(f"\n✅ Successfully saved recommendation report to: {OUTPUT_FILE}")
        safe_print(f"\n✅ Successfully saved recommendation report to: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"❌ Failed to write final report: {e}")
        safe_print(f"❌ Failed to write final report: {e}")

    end_time = time.time()
    logger.info(f"Total time taken: {end_time - start_time:.2f} seconds.")
    safe_print(f"Total time taken: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()