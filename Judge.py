"""
Judge
Version: 2.0 (Task Card #4: Migrated to Version History)
Date: 2025-11-10

This script acts as an impartial "Judge" for claims from all databases.
It orchestrates a multi-step judgment process:
1.  PHASE 1: Judge all 'pending' claims from version history.
2.  PHASE 2: Pass all rejected claims to the DeepRequirementsAnalyzer (DRA).
3.  PHASE 3: Judge the *new* claims re-submitted by the DRA.
4.  PHASE 4: Save all final verdicts back to version history.

This version migrates from deep_coverage_database.json to review_version_history.json
as the single source of truth for all claims.
"""

import os
import sys
import json
import csv
import time
import hashlib
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
import numpy as np
import logging
import warnings
import re               # For normalization
import difflib          # For fuzzy matching

# --- NEW: Import the Deep Requirements Analyzer ---
import DeepRequirementsAnalyzer as dra

# --- CONFIGURATION ---
load_dotenv()

# 1. Input Files
DEFINITIONS_FILE = 'pillar_definitions_enhanced.json'

# 2. Input/Output Files
# DEPRECATED: DEEP_COVERAGE_DB_FILE = 'deep_coverage_database.json'
# Now using version history as single source of truth (Task Card #4)
VERSION_HISTORY_FILE = 'review_version_history.json'
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'

# 3. Path/API Config
CACHE_DIR = 'judge_cache'
API_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "API_CALLS_PER_MINUTE": 60,
    "MATCH_CONFIDENCE_THRESHOLD": 0.8 # Match must be 80% similar
}

# (Setup code, Logging, and UTF8Formatter are identical)
# ...
# --- Logging Setup ---
class UTF8Formatter(logging.Formatter):
    """Custom formatter that handles Unicode properly on Windows"""
    def format(self, record):
        if hasattr(record, 'msg'):
            record.msg = str(record.msg)
        try:
            return super().format(record)
        except UnicodeEncodeError:
            record.msg = record.msg.encode('utf-8', 'replace').decode('utf-8')
            return super().format(record)

log_handlers = []
file_handler = logging.FileHandler('judge.log', encoding='utf-8')
file_handler.setFormatter(UTF8Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_handlers.append(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(UTF8Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_handlers.append(console_handler)
logging.basicConfig(level=logging.INFO, handlers=log_handlers)
logger = logging.getLogger(__name__)

def safe_print(message):
    """Print message safely handling Unicode on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(str(message).encode(sys.stdout.encoding or 'utf-8', 'replace').decode(sys.stdout.encoding or 'utf-8'))

os.makedirs(CACHE_DIR, exist_ok=True)
# --- End Logging Setup ---


# --- Data Structure Definition (Unchanged) ---
class PaperAnalyzer:
    """Stub class to hold the master list of CSV headers in the correct order."""
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


# --- APIManager CLASS (MODIFIED) ---
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

            # --- MODIFICATION: Added text_generation_config ---

            # Config for JSON (used by Judge & DRA)
            self.json_generation_config = types.GenerateContentConfig(
                temperature=0.0,
                top_p=1.0,
                top_k=1,
                max_output_tokens=16384,
                response_mime_type="application/json",
                thinking_config=thinking_config
            )

            # Config for Text (in case any module needs it)
            self.text_generation_config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=1.0,
                top_k=1,
                max_output_tokens=16384,
                thinking_config=thinking_config
            )
            # --- END MODIFICATION ---

            logger.info(f"[SUCCESS] Gemini Client (google-ai SDK) initialized (Thinking Disabled).")
            safe_print(f"✅ Gemini Client initialized successfully (Thinking Disabled).")
        except Exception as e:
            logger.critical(f"[ERROR] Critical Error initializing Gemini Client: {e}")
            safe_print(f"❌ Critical Error initializing Gemini Client: {e}")
            raise

    def rate_limit(self):
        # (This function is unchanged)
        current_time = time.time()
        if current_time - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = current_time
        if self.calls_this_minute >= API_CONFIG['API_CALLS_PER_MINUTE']:
            sleep_time = 60.1 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.info(
                    f"Rate limit ({API_CONFIG['API_CALLS_PER_MINUTE']}/min) reached. Sleeping for {sleep_time:.1f} seconds...")
                safe_print(f"⏳ Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
                self.calls_this_minute = 0
                self.minute_start = time.time()
        self.calls_this_minute += 1

    # --- MODIFIED: cached_api_call now accepts 'is_json' ---
    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        if use_cache and prompt_hash in self.cache:
            logger.debug(f"Cache hit for hash: {prompt_hash}")
            safe_print("📦 Using cached response")
            return self.cache[prompt_hash]

        logger.debug(f"Cache miss for hash: {prompt_hash}. Calling API...")
        self.rate_limit()

        response_text = ""
        for attempt in range(API_CONFIG['RETRY_ATTEMPTS']):
            try:
                # --- MODIFICATION: Select correct config ---
                current_config_object = self.json_generation_config if is_json else self.text_generation_config

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=current_config_object
                )
                response_text = response.text

                # --- MODIFICATION: Parse based on 'is_json' ---
                if is_json:
                    result = json.loads(response_text)
                else:
                    result = response_text
                # --- END MODIFICATION ---

                self.cache[prompt_hash] = result
                return result

            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error on attempt {attempt + 1}: {e}. Response text: '{response_text[:500]}...'")
                if attempt < API_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(API_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for JSON decode error.")
            except Exception as e:
                if "DeadlineExceeded" in str(e) or "Timeout" in str(e):
                    logger.error(f"API call timed out on attempt {attempt + 1}")
                else:
                    logger.error(f"API error on attempt {attempt + 1}: {type(e).__name__} - {e}")
                if "429" in str(e):
                    logger.warning("Rate limit error detected by API, increasing sleep time.")
                    time.sleep(API_CONFIG['RETRY_DELAY'] * (attempt + 2))
                elif attempt < API_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(API_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for API error.")

        logger.error(f"API call failed after {API_CONFIG['RETRY_ATTEMPTS']} attempts.")
        return None
# --- END APIManager MODIFICATION ---


# --- Robust Lookup & Normalization (Unchanged) ---
DEFINITIONS_LOOKUP_MAP = {}
CANONICAL_PILLAR_MAP = {}

def _normalize_string(s: str) -> str:
    if not isinstance(s, str): return ""
    s = re.sub(r'^(SR|Sub-)[\d\.]+:?\s*', '', s, flags=re.IGNORECASE)
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def _build_lookup_map(pillar_definitions: Dict):
    global DEFINITIONS_LOOKUP_MAP, CANONICAL_PILLAR_MAP
    for pillar_key, pillar_data in pillar_definitions.items():
        norm_pillar = _normalize_string(pillar_key.split(':')[0])
        CANONICAL_PILLAR_MAP[norm_pillar] = pillar_key
        for req_key, sub_req_list in pillar_data.get("requirements", {}).items():
            for sub_req_string in sub_req_list:
                norm_sub_req = _normalize_string(sub_req_string)
                if norm_sub_req not in DEFINITIONS_LOOKUP_MAP:
                    DEFINITIONS_LOOKUP_MAP[norm_sub_req] = sub_req_string
                else:
                    logger.warning(f"Duplicate normalized sub-req key found: {norm_sub_req}")
    logger.info(f"Built definition lookup map with {len(DEFINITIONS_LOOKUP_MAP)} sub-reqs.")

def find_robust_sub_requirement_text(claim_sub_req: str) -> Optional[str]:
    if not DEFINITIONS_LOOKUP_MAP:
        logger.error("DEFINITIONS_LOOKUP_MAP is not built. Cannot match.")
        return None
    norm_claim = _normalize_string(claim_sub_req)
    if norm_claim in DEFINITIONS_LOOKUP_MAP:
        return DEFINITIONS_LOOKUP_MAP[norm_claim]
    matches = difflib.get_close_matches(
        norm_claim,
        DEFINITIONS_LOOKUP_MAP.keys(),
        n=1,
        cutoff=API_CONFIG["MATCH_CONFIDENCE_THRESHOLD"]
    )
    if matches:
        best_match_key = matches[0]
        canonical_string = DEFINITIONS_LOOKUP_MAP[best_match_key]
        logger.warning(f"Fuzzy match found: '{claim_sub_req}' -> '{canonical_string}'")
        return canonical_string
    logger.error(f"Could not find any match for claim: '{claim_sub_req}' (Normalized: '{norm_claim}')")
    return None

def find_robust_pillar_key(claim_pillar: str) -> Optional[str]:
    norm_claim_pillar = _normalize_string(claim_pillar.split(':')[0])
    if norm_claim_pillar in CANONICAL_PILLAR_MAP:
        return CANONICAL_PILLAR_MAP[norm_claim_pillar]
    matches = difflib.get_close_matches(
        norm_claim_pillar,
        CANONICAL_PILLAR_MAP.keys(),
        n=1,
        cutoff=API_CONFIG["MATCH_CONFIDENCE_THRESHOLD"]
    )
    if matches:
        best_match_key = matches[0]
        canonical_string = CANONICAL_PILLAR_MAP[best_match_key]
        logger.warning(f"Fuzzy match found for pillar: '{claim_pillar}' -> '{canonical_string}'")
        return canonical_string
    logger.error(f"Could not find any pillar match for: '{claim_pillar}'")
    return None
# --- END Lookup Logic ---


# --- DATA LOADING FUNCTIONS ---
def load_version_history(filepath: str) -> Dict:
    """
    Loads the review version history (source of truth).
    Returns a dict keyed by filename.
    """
    if not os.path.exists(filepath):
        logger.warning(f"Version history file not found: {filepath}. Creating new one.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            history = json.load(f)
        logger.info(f"Loaded version history for {len(history)} files from {filepath}")
        return history
    except json.JSONDecodeError:
        logger.warning(f"Error decoding {filepath}. Starting with empty history.")
        return {}
    except Exception as e:
        logger.error(f"Error loading version history: {e}")
        return {}


def save_version_history(filepath: str, history: Dict):
    """Saves the updated version history."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved version history for {len(history)} files to {filepath}")
    except Exception as e:
        logger.error(f"Error saving version history: {e}")


def load_pillar_definitions(filepath: str) -> Dict:
    if not os.path.exists(filepath):
        logger.error(f"Pillar definitions file not found: {filepath}. Cannot judge.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            definitions = json.load(f)
        _build_lookup_map(definitions)
        return definitions
    except Exception as e:
        logger.error(f"Error loading pillar definitions: {e}")
        return {}

def load_research_db(filepath: str) -> List[Dict]:
    if not os.path.exists(filepath):
        logger.error(f"Research DB file not found: {filepath}. Cannot judge CSV claims.")
        return []
    try:
        df = pd.read_csv(filepath, encoding='utf-8')
        df = df.replace({pd.NA: None, np.nan: None})
        records = df.to_dict('records')
        parsed_records = []
        for row in records:
            req_data = row.get("Requirement(s)")
            if req_data and isinstance(req_data, str):
                try:
                    row["Requirement(s)"] = json.loads(req_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse 'Requirement(s)' for {row.get('FILENAME')}. Treating as empty.")
                    row["Requirement(s)"] = []
            elif not req_data or not isinstance(req_data, list):
                row["Requirement(s)"] = []
            parsed_records.append(row)
        logger.info(f"Loaded and parsed {len(parsed_records)} records from {filepath}")
        return parsed_records
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file is empty: {filepath}")
        return []
    except Exception as e:
        logger.error(f"Could not load or parse research DB {filepath}: {e}")
        return []

def save_research_db(filepath: str, data: List[Dict]):
    if not data:
        logger.warning("No data to save to research DB.")
        return
    try:
        fieldnames = PaperAnalyzer.DATABASE_COLUMN_ORDER.copy()
        all_data_keys = set().union(*(d.keys() for d in data))
        extra_keys = sorted(list(all_data_keys - set(fieldnames)))
        final_fieldnames = fieldnames + extra_keys
        if extra_keys:
            logger.warning(f"Found {len(extra_keys)} keys in data not in standard column order. Appending to end: {extra_keys}")

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=final_fieldnames, restval='', extrasaction='ignore', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in data:
                row_to_write = row.copy()
                if "Requirement(s)" in row_to_write:
                    req_list = row_to_write["Requirement(s)"]
                    row_to_write["Requirement(s)"] = json.dumps(req_list) if req_list else ""
                row_to_write.pop('_origin', None)
                row_to_write.pop('_origin_list', None)
                row_to_write.pop('_filename', None)
                writer.writerow(row_to_write)
        logger.info(f"Successfully saved {len(data)} records back to {filepath} with correct column order.")
    except PermissionError:
        logger.error(f"PERMISSION ERROR: Could not write to {filepath}. Is the file open in Excel?")
        safe_print(f"❌ PERMISSION ERROR: Could not write to {filepath}. Please close it and try again.")
    except Exception as e:
        logger.error(f"Failed to save research DB to {filepath}: {e}")
        safe_print(f"❌ CRITICAL: Failed to save updated CSV. See log.")
# --- END DATA LOADING ---


# --- CORE LOGIC FUNCTIONS (Unchanged) ---

def build_judge_prompt(claim: Dict, sub_requirement_definition: str) -> str:
    sub_req_key = claim.get('sub_requirement') or claim.get('sub_requirement_key', 'N/A')
    return f"""
You are an impartial "Judge" AI...
(Prompt text is identical)
...
Return ONLY a clean JSON object with this exact structure:
{{
  "verdict": "approved|rejected",
  "judge_notes": "A 1-sentence explanation for your decision, starting with 'Approved.' or 'Rejected.'."
}}
"""

def validate_judge_response(response: Any) -> Optional[Dict]:
    if not isinstance(response, dict):
        return None
    verdict = response.get("verdict")
    notes = response.get("judge_notes")
    if verdict not in ["approved", "rejected"] or not isinstance(notes, str) or not notes:
        return None
    return response

# --- MAIN EXECUTION (Unchanged) ---
def main():
    start_time = time.time()
    logger.info("\n" + "=" * 80)
    logger.info("JUDGE PIPELINE v1.6 (Fixes APIManager bug for DRA calls)")
    logger.info("=" * 80)

    logger.info("\n=== INITIALIZING COMPONENTS ===")
    safe_print("\n=== INITIALIZING COMPONENTS ===")
    try:
        api_manager = APIManager() # This will now be the *corrected* version
    except Exception as init_e:
        logger.critical(f"Failed to initialize core components: {init_e}")
        safe_print(f"❌ Failed to initialize core components: {init_e}")
        return

    papers_folder_path = dra.find_papers_folder()
    if not papers_folder_path:
        logger.error("Could not find PAPERS_FOLDER. DRA will fail.")
        safe_print("❌ Could not find PAPERS_FOLDER. DRA will be skipped.")

    logger.info("\n=== LOADING DATABASES ===")
    safe_print("\n=== LOADING DATABASES ===")

    version_history = load_version_history(VERSION_HISTORY_FILE)
    pillar_definitions = load_pillar_definitions(DEFINITIONS_FILE)

    if not pillar_definitions:
        logger.critical("Missing pillar definitions. Exiting.")
        safe_print("❌ Missing pillar definitions. Exiting.")
        return
    if not version_history:
        logger.critical("Missing version history. Exiting.")
        safe_print("❌ Missing version history. Exiting.")
        return

    # --- Build the unified "docket" from version history ---
    claims_to_judge = []
    for filename, versions in version_history.items():
        if not versions:
            continue
        # Get latest version
        latest_version = versions[-1]
        review = latest_version.get('review', {})
        requirements_list = review.get('Requirement(s)', [])
        
        for claim in requirements_list:
            if claim.get("status") == "pending_judge_review":
                claim['_origin'] = 'version_history'
                claim['_filename'] = filename
                claim['_requirements_list'] = requirements_list  # Keep reference for update
                claims_to_judge.append(claim)
    if not claims_to_judge:
        logger.info("No pending claims found in any database.")
        safe_print("⚖️ No pending claims found. All work is done.")
        return
    logger.info(f"Found {len(claims_to_judge)} total claims pending judgment from all sources.")
    safe_print(f"⚖️ Found {len(claims_to_judge)} total claims pending judgment. The court is in session.")

    # --- PHASE 1: Initial Judgment ---
    logger.info("\n--- PHASE 1: Initial Judgment ---")
    safe_print("\n--- PHASE 1: Initial Judgment ---")

    init_approved_count = 0
    init_rejected_count = 0
    claims_for_dra_appeal = []

    for i, claim in enumerate(claims_to_judge, 1):
        filename = claim.get('filename') or claim.get('_filename', 'N/A')
        claim_id_short = f"{filename[:15]}... ({claim['claim_id'][:6]})"
        logger.info(f"\n--- Judging Claim {i}/{len(claims_to_judge)}: {claim_id_short} ---")
        safe_print(f"\n--- Judging Claim {i}/{len(claims_to_judge)}: {claim_id_short} ---")

        try:
            sub_req_key = claim.get('sub_requirement') or claim.get('sub_requirement_key', 'N/A')
            pillar_key = claim.get('pillar', 'N/A')
            definition_text = find_robust_sub_requirement_text(sub_req_key)

            if not definition_text:
                logger.error(f"  Could not find definition for claim. Rejecting.")
                safe_print(f"  ❌ Could not find definition for '{sub_req_key}'. Rejecting.")
                ruling = {"verdict": "rejected", "judge_notes": f"Rejected. Could not find sub-requirement definition for '{sub_req_key}' in pillar file."}
            else:
                prompt = build_judge_prompt(claim, definition_text)
                logger.info(f"  Submitting claim to Judge AI...")
                safe_print(f"  Submitting claim to Judge AI...")
                response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True) # is_json=True is now valid
                ruling = validate_judge_response(response)

            if ruling:
                canonical_pillar = find_robust_pillar_key(pillar_key)
                canonical_sub_req = definition_text
                if canonical_pillar: claim['pillar'] = canonical_pillar
                if canonical_sub_req:
                    claim['sub_requirement'] = canonical_sub_req
                    claim.pop('sub_requirement_key', None)

                claim['status'] = ruling['verdict']
                claim['judge_notes'] = ruling['judge_notes']
                claim['judge_timestamp'] = datetime.now().isoformat()

                if ruling['verdict'] == 'approved':
                    logger.info(f"  VERDICT: APPROVED")
                    safe_print(f"  ✅ VERDICT: APPROVED")
                    init_approved_count += 1
                else:
                    logger.info(f"  VERDICT: REJECTED (Pending DRA)")
                    safe_print(f"  ❌ VERDICT: REJECTED (Sending to DRA for appeal)")
                    init_rejected_count += 1
                    claims_for_dra_appeal.append(claim)

                logger.info(f"  Note: {ruling['judge_notes']}")
            else:
                logger.error(f"  Judge AI returned invalid response. Claim will be re-judged next run.")
                safe_print(f"  ⚠️ Judge AI returned invalid response. Skipping for next run.")
        except Exception as e:
            logger.critical(f"  CRITICAL UNHANDLED ERROR on claim {claim['claim_id']}: {e}")
            safe_print(f"  ❌ CRITICAL ERROR on claim. See log. Skipping.")

    # --- PHASE 2: DRA Appeal Process ---
    logger.info("\n--- PHASE 2: DRA Appeal Process ---")
    safe_print("\n--- PHASE 2: DRA Appeal Process ---")

    new_claims_for_rejudgment = []
    if not claims_for_dra_appeal:
        logger.info("No rejected claims to send to DRA.")
        safe_print("⚖️ No rejected claims to send to DRA. Skipping appeal process.")
    elif not papers_folder_path:
        logger.error("PAPERS_FOLDER not found. Skipping DRA appeal process.")
        safe_print("❌ PAPERS_FOLDER not found. Skipping DRA appeal process.")
    else:
        safe_print(f"⚖️ Sending {len(claims_for_dra_appeal)} rejected claims to Deep Requirements Analyzer for appeal...")
        new_claims_for_rejudgment = dra.run_analysis(
            claims_for_dra_appeal,
            api_manager,
            papers_folder_path
        )

    # --- PHASE 3: Final Judgment (on Appeals) ---
    logger.info("\n--- PHASE 3: Final Judgment (on Appeals) ---")
    safe_print("\n--- PHASE 3: Final Judgment (on Appeals) ---")

    dra_approved_count = 0
    dra_rejected_count = 0

    if not new_claims_for_rejudgment:
        logger.info("DRA did not re-submit any new claims.")
        safe_print("⚖️ DRA did not re-submit any new claims.")
    else:
        logger.info(f"DRA re-submitted {len(new_claims_for_rejudgment)} new claims. Starting final judgment...")
        safe_print(f"⚖️ DRA re-submitted {len(new_claims_for_rejudgment)} new claims. Starting final judgment...")

        for i, new_claim in enumerate(new_claims_for_rejudgment, 1):
            filename = new_claim.get('filename', 'N/A')
            claim_id_short = f"{filename[:15]}... ({new_claim['claim_id'][:6]})"
            logger.info(f"\n--- Re-Judging Claim {i}/{len(new_claims_for_rejudgment)}: {claim_id_short} ---")
            safe_print(f"\n--- Re-Judging Claim {i}/{len(new_claims_for_rejudgment)}: {claim_id_short} ---")

            try:
                sub_req_key = new_claim.get('sub_requirement', 'N/A')
                pillar_key = new_claim.get('pillar', 'N/A')
                definition_text = find_robust_sub_requirement_text(sub_req_key)

                if not definition_text:
                    logger.error(f"  Could not find definition for DRA claim. Rejecting.")
                    safe_print(f"  ❌ Could not find definition for '{sub_req_key}'. Rejecting.")
                    ruling = {"verdict": "rejected", "judge_notes": f"Rejected. (DRA Appeal) Could not find sub-requirement definition for '{sub_req_key}'."}
                else:
                    prompt = build_judge_prompt(new_claim, definition_text)
                    logger.info(f"  Submitting DRA claim to Judge AI...")
                    safe_print(f"  Submitting DRA claim to Judge AI...")
                    response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True) # is_json=True is now valid
                    ruling = validate_judge_response(response)

                if ruling:
                    new_claim['status'] = ruling['verdict']
                    new_claim['judge_notes'] = ruling['judge_notes']
                    new_claim['judge_timestamp'] = datetime.now().isoformat()

                    if ruling['verdict'] == 'approved':
                        logger.info(f"  VERDICT (Appeal): APPROVED")
                        safe_print(f"  ✅ VERDICT (Appeal): APPROVED")
                        dra_approved_count += 1
                    else:
                        logger.info(f"  VERDICT (Appeal): REJECTED")
                        safe_print(f"  ❌ VERDICT (Appeal): REJECTED")
                        dra_rejected_count += 1

                    if new_claim.get('_origin') == 'csv_db':
                        new_claim['_origin_list'].append(new_claim)
                    else:
                        db_json_data.append(new_claim)

                else:
                    logger.error(f"  Judge AI returned invalid response for DRA claim. Claim is lost.")
                    safe_print(f"  ⚠️ Judge AI returned invalid response for DRA claim. Skipping.")

            except Exception as e:
                logger.critical(f"  CRITICAL UNHANDLED ERROR on DRA claim {new_claim['claim_id']}: {e}")
                safe_print(f"  ❌ CRITICAL ERROR on DRA claim. See log. Skipping.")


    # --- PHASE 4: Save All Results ---
    logger.info("\n--- PHASE 4: Saving All Results ---")

    # We now save the version history, which includes:
    # 1. Claims from Phase 1 that were 'approved'
    # 2. Claims from Phase 1 that were 'rejected' (and not successfully appealed)
    # 3. New claims from Phase 3 that were 'approved'
    # 4. New claims from Phase 3 that were 'rejected'
    # All claims are already updated in-place in version_history

    save_version_history(VERSION_HISTORY_FILE, version_history)

    logger.info("\n" + "=" * 80)
    logger.info("JUDGMENT COMPLETE")
    safe_print("\n" + "=" * 80)
    safe_print("⚖️ Judgment Complete. The court is adjourned.")
    safe_print("--- Phase 1: Initial Judgment ---")
    safe_print(f"  Total Claims Judged: {init_approved_count + init_rejected_count}")
    safe_print(f"  ✅ Initial Approved: {init_approved_count}")
    safe_print(f"  ❌ Initial Rejected (Sent to DRA): {init_rejected_count}")
    safe_print("--- Phase 3: DRA Appeal Judgment ---")
    safe_print(f"  Total Claims Re-Submitted by DRA: {len(new_claims_for_rejudgment)}")
    safe_print(f"  ✅ DRA Appeal Approved: {dra_approved_count}")
    safe_print(f"  ❌ DRA Appeal Rejected: {dra_rejected_count}")
    safe_print("\n  Database updated:")
    safe_print(f"    - {VERSION_HISTORY_FILE}")
    safe_print(f"  Note: Run sync_history_to_db.py to update the CSV database.")

    end_time = time.time()
    logger.info(f"Total time taken: {end_time - start_time:.2f} seconds.")
    safe_print(f"Total time taken: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()