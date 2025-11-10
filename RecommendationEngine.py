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
from google import genai
from google.genai import types
from dotenv import load_dotenv
import logging
import pickle
from sentence_transformers import SentenceTransformer
import warnings

# --- CONFIGURATION & SETUP ---
load_dotenv()

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.file_download")
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# File paths
GAP_REPORT_FILE = 'gap_analysis_output/gap_analysis_report.json'
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'
OUTPUT_FILE = 'suggested_searches.md'
CACHE_DIR = 'recommender_cache'  # Separate cache for this script

# Analysis configuration
ANALYSIS_CONFIG = {
    'COMPLETENESS_THRESHOLD': 80,  # Find gaps with completeness < this value
    'API_CALLS_PER_MINUTE': 60,
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5
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


# --- APIMANAGER CLASS (Copied from Reviewer v3.1) ---

class APIManager:
    """Manages API calls with rate limiting, caching, and retry logic"""

    def __init__(self):
        self.cache = {}
        self.last_call_time = 0
        self.calls_this_minute = 0
        self.minute_start = time.time()

        try:
            self.client = genai.Client()

            thinking_config = types.ThinkingConfig(thinking_budget=0)

            # Config for JSON responses
            self.json_generation_config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=1.0,
                top_k=1,
                max_output_tokens=16384,
                response_mime_type="application/json",
                thinking_config=thinking_config
            )

            # Config for TEXT responses (for summarization)
            self.text_generation_config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=1.0,
                top_k=1,
                max_output_tokens=16384,
                thinking_config=thinking_config
            )

            logger.info(f"[SUCCESS] Gemini Client (google-ai SDK) initialized (Thinking Disabled).")
            safe_print(f"✅ Gemini Client initialized successfully (Thinking Disabled).")
        except Exception as e:
            logger.critical(f"[ERROR] Critical Error initializing Gemini Client: {e}")
            safe_print(f"❌ Critical Error initializing Gemini Client: {e}")
            raise

        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("[SUCCESS] Sentence Transformer initialized.")
            safe_print("✅ Sentence Transformer initialized.")
        except Exception as e:
            logger.warning(f"[WARNING] Could not initialize Sentence Transformer: {e}")
            safe_print(f"⚠️ Could not initialize Sentence Transformer: {e}")
            self.embedder = None

    def rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        if current_time - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = current_time

        if self.calls_this_minute >= ANALYSIS_CONFIG['API_CALLS_PER_MINUTE']:
            sleep_time = 60.1 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.info(
                    f"Rate limit ({ANALYSIS_CONFIG['API_CALLS_PER_MINUTE']}/min) reached. Sleeping for {sleep_time:.1f} seconds...")
                safe_print(f"⏳ Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
                self.calls_this_minute = 0
                self.minute_start = time.time()
        self.calls_this_minute += 1

    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
        """Make API call with caching and retry logic"""
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()

        if use_cache and prompt_hash in self.cache:
            logger.debug(f"Cache hit for hash: {prompt_hash}")
            safe_print("📦 Using cached response")
            return self.cache[prompt_hash]

        logger.debug(f"Cache miss for hash: {prompt_hash}. Calling API...")
        self.rate_limit()

        response_text = ""  # Initialize to avoid UnboundLocalError
        for attempt in range(ANALYSIS_CONFIG['RETRY_ATTEMPTS']):
            try:
                current_config_object = self.json_generation_config if is_json else self.text_generation_config

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=current_config_object
                )

                response_text = response.text
                if is_json:
                    result = json.loads(response_text)
                else:
                    result = response_text
                self.cache[prompt_hash] = result
                return result
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error on attempt {attempt + 1}: {e}. Response text: '{response_text[:500]}...'")
                if attempt < ANALYSIS_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(ANALYSIS_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for JSON decode error.")
            except Exception as e:
                if "DeadlineExceeded" in str(e) or "Timeout" in str(e):
                    logger.error(f"API call timed out on attempt {attempt + 1}")
                else:
                    logger.error(f"API error on attempt {attempt + 1}: {type(e).__name__} - {e}")

                if "429" in str(e):
                    logger.warning("Rate limit error detected by API, increasing sleep time.")
                    time.sleep(ANALYSIS_CONFIG['RETRY_DELAY'] * (attempt + 2))
                elif attempt < ANALYSIS_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(ANALYSIS_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for API error.")

        logger.error(f"API call failed after {ANALYSIS_CONFIG['RETRY_ATTEMPTS']} attempts.")
        return None


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