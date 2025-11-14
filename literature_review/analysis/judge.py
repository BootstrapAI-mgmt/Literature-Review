"""
Judge
Version: 2.0 (Uses Version History as Single Source of Truth)
Date: 2025-11-10

This script acts as an impartial "Judge" for claims from version history.
It orchestrates a multi-step judgment process:
1.  PHASE 1: Judge all 'pending_judge_review' claims from version history.
2.  PHASE 2: Pass all rejected claims to the DeepRequirementsAnalyzer (DRA).
3.  PHASE 3: Judge the *new* claims re-submitted by the DRA.
4.  PHASE 4: Save all final verdicts to version history ONLY.

This version refactors to use review_version_history.json as the single
source of truth, eliminating direct writes to CSV and deep_coverage_database.json.
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
import google.generativeai as genai
from google.generativeai import types
from dotenv import load_dotenv
import numpy as np
import logging
import warnings
import re               # For normalization
import difflib          # For fuzzy matching
from collections import defaultdict  # For grouping claims by file

# --- NEW: Import the Deep Requirements Analyzer ---
from . import requirements as dra

# --- CONFIGURATION ---
load_dotenv()

# 1. Input Files
DEFINITIONS_FILE = 'pillar_definitions.json'

# 2. Input/Output Files
# DEPRECATED: DEEP_COVERAGE_DB_FILE = 'deep_coverage_database.json'
# DEPRECATED: RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'

# 3. Path/API Config
CACHE_DIR = 'judge_cache'
API_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "API_CALLS_PER_MINUTE": 60,
    "MATCH_CONFIDENCE_THRESHOLD": 0.8, # Match must be 80% similar
    "CLAIM_BATCH_SIZE": 10  # Process claims in batches to handle large datasets
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


# --- DATA LOADING FUNCTIONS (MODIFIED) ---
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

# --- END DATA LOADING ---


# --- VERSION HISTORY I/O FUNCTIONS ---
VERSION_HISTORY_FILE = 'review_version_history.json'

def load_version_history(filepath: str = VERSION_HISTORY_FILE) -> Dict:
    """Loads the review version history (source of truth)."""
    if not os.path.exists(filepath):
        logger.warning(f"Version history file not found: {filepath}. Starting fresh.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            history = json.load(f)
        logger.info(f"Loaded history for {len(history)} files from {filepath}")
        return history
    except Exception as e:
        logger.error(f"Failed to load version history from {filepath}: {e}")
        return {}

def save_version_history(filepath: str, history: Dict):
    """Saves updated review version history."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved version history to {filepath}")
    except Exception as e:
        logger.error(f"Error saving version history to {filepath}: {e}")
        safe_print(f"❌ CRITICAL: Failed to save version history: {e}")

def extract_pending_claims_from_history(history: Dict) -> List[Dict]:
    """Extracts all pending claims from version history."""
    claims = []
    for filename, versions in history.items():
        if not versions:
            continue
        latest = versions[-1].get('review', {})
        for claim in latest.get('Requirement(s)', []):
            if claim.get('status') == 'pending_judge_review':
                # Add metadata for tracking
                claim['_source_filename'] = filename
                claim['_source_type'] = 'version_history'
                claims.append(claim)
    logger.info(f"Extracted {len(claims)} pending claims from version history")
    return claims

def update_claims_in_history(history: Dict, updated_claims: List[Dict]) -> Dict:
    """Updates claim statuses in version history and creates new version entries."""
    # Create lookup by claim_id
    claims_by_id = {c['claim_id']: c for c in updated_claims}
    
    timestamp = datetime.now().isoformat()
    updated_files = []
    
    for filename, versions in history.items():
        if not versions:
            continue
        
        latest = versions[-1]
        requirements = latest.get('review', {}).get('Requirement(s)', [])
        
        # Track if any claims were updated for this file
        file_updated = False
        updated_claim_ids = []
        
        for claim in requirements:
            if claim['claim_id'] in claims_by_id:
                updated = claims_by_id[claim['claim_id']]
                claim['status'] = updated['status']
                claim['judge_notes'] = updated['judge_notes']
                claim['judge_timestamp'] = updated['judge_timestamp']
                file_updated = True
                updated_claim_ids.append(claim['claim_id'])
        
        # Add new version entry if file was updated
        if file_updated:
            new_version = {
                'timestamp': timestamp,
                'review': latest['review'],  # Copy of entire review with updated claims
                'changes': {
                    'status': 'judge_update',
                    'updated_claims': len(updated_claim_ids),
                    'claim_ids': updated_claim_ids
                }
            }
            versions.append(new_version)
            updated_files.append(filename)
    
    logger.info(f"Updated {len(updated_files)} files in version history")
    return history

def add_new_claims_to_history(history: Dict, new_claims: List[Dict]) -> Dict:
    """Adds new claims (from DRA) to version history."""
    timestamp = datetime.now().isoformat()
    claims_by_file = defaultdict(list)
    
    # Group claims by filename
    for claim in new_claims:
        filename = claim.get('_source_filename') or claim.get('filename')
        if filename:
            claims_by_file[filename].append(claim)
    
    for filename, claims in claims_by_file.items():
        if filename not in history:
            logger.warning(f"File {filename} not in history. Skipping new claims.")
            continue
        
        versions = history[filename]
        if not versions:
            continue
        
        latest = versions[-1]
        latest['review']['Requirement(s)'].extend(claims)
        
        # Add new version entry
        new_version = {
            'timestamp': timestamp,
            'review': latest['review'],
            'changes': {
                'status': 'dra_appeal',
                'new_claims': len(claims),
                'claim_ids': [c['claim_id'] for c in claims]
            }
        }
        versions.append(new_version)
    
    logger.info(f"Added {len(new_claims)} new claims to version history")
    return history
# --- END VERSION HISTORY I/O FUNCTIONS ---


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

def process_claims_in_batches(claims: List[Dict], batch_size: int) -> List[List[Dict]]:
    """
    Split claims into batches for processing.
    This helps manage memory and API timeouts when processing large datasets.
    """
    batches = []
    for i in range(0, len(claims), batch_size):
        batch = claims[i:i + batch_size]
        batches.append(batch)
    return batches


# --- ENHANCED EVIDENCE SCORING FUNCTIONS (Task Card #16) ---

def build_judge_prompt_enhanced(claim: Dict, sub_requirement_definition: str) -> str:
    """
    Enhanced prompt with multi-dimensional scoring.
    
    Returns prompt requesting 6-dimensional evidence quality scores
    following PRISMA systematic review standards.
    """
    sub_req_key = claim.get('sub_requirement') or claim.get('sub_requirement_key', 'N/A')
    return f"""
You are an impartial "Judge" AI evaluating scientific evidence quality.

**Claim to Evaluate:**
{json.dumps(claim, indent=2)}

**Target Requirement:**
{sub_requirement_definition}

**Your Task:**
Assess this claim using PRISMA systematic review standards across 6 dimensions:

1. **Strength of Evidence** (1-5):
   - 5: Strong (Multiple RCTs, meta-analysis, direct experimental proof)
   - 4: Moderate (Single well-designed study, clear experimental validation)
   - 3: Weak (Observational study, indirect evidence)
   - 2: Very Weak (Case reports, anecdotal evidence)
   - 1: Insufficient (Opinion, speculation, no empirical support)

2. **Methodological Rigor** (1-5):
   - 5: Gold standard (Randomized controlled trial, peer-reviewed, replicated)
   - 4: Controlled study (Experimental with controls, proper statistics)
   - 3: Observational (Real-world data, no controls)
   - 2: Case study (Single instance, n=1)
   - 1: Opinion (Expert opinion without empirical basis)

3. **Relevance to Requirement** (1-5):
   - 5: Perfect match (Directly addresses this exact requirement)
   - 4: Strong (Clearly related, minor gap)
   - 3: Moderate (Related but requires inference)
   - 2: Tangential (Peripherally related)
   - 1: Weak (Very indirect connection)

4. **Evidence Directness** (1-3):
   - 3: Direct (Paper explicitly states this finding)
   - 2: Indirect (Finding can be inferred from results)
   - 1: Inferred (Requires significant interpretation)

5. **Recency Bonus**:
   - true if published within last 3 years, false otherwise

6. **Reproducibility** (1-5):
   - 5: Code + data publicly available
   - 4: Detailed methods, replicable
   - 3: Basic methods described
   - 2: Vague methods
   - 1: No methodological detail

**Decision Criteria:**
- APPROVE if composite_score ≥ 3.0 AND strength_score ≥ 3 AND relevance_score ≥ 3
- REJECT otherwise

**Return Format (JSON only):**
{{
  "verdict": "approved|rejected",
  "evidence_quality": {{
    "strength_score": <1-5>,
    "strength_rationale": "<brief justification>",
    "rigor_score": <1-5>,
    "study_type": "experimental|observational|theoretical|review|opinion",
    "relevance_score": <1-5>,
    "relevance_notes": "<brief explanation>",
    "directness": <1-3>,
    "is_recent": <true|false>,
    "reproducibility_score": <1-5>,
    "composite_score": <calculated weighted average>,
    "confidence_level": "high|medium|low"
  }},
  "judge_notes": "<1-2 sentence summary>"
}}

**Composite Score Formula:**
composite_score = (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
"""


def calculate_composite_score(quality: Dict) -> float:
    """
    Calculate composite evidence quality score.
    
    Formula: (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) 
             + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
    """
    weights = {
        "strength_score": 0.30,
        "rigor_score": 0.25,
        "relevance_score": 0.25,
        "directness": 0.10,  # Normalized to 0-1 range (divide by 3)
        "is_recent": 0.05,   # Boolean treated as 0 or 1
        "reproducibility_score": 0.05
    }
    
    score = 0.0
    score += quality["strength_score"] * weights["strength_score"]
    score += quality["rigor_score"] * weights["rigor_score"]
    score += quality["relevance_score"] * weights["relevance_score"]
    score += (quality["directness"] / 3.0) * weights["directness"]  # Normalize to 0-1
    score += (1.0 if quality["is_recent"] else 0.0) * weights["is_recent"]
    score += quality["reproducibility_score"] * weights["reproducibility_score"]
    
    return round(score, 2)


def validate_judge_response_enhanced(response: Any) -> Optional[Dict]:
    """Validate enhanced Judge response with quality scores."""
    if not isinstance(response, dict):
        return None
    
    # Check required fields
    if "verdict" not in response or "evidence_quality" not in response:
        return None
    
    verdict = response["verdict"]
    if verdict not in ["approved", "rejected"]:
        return None
    
    quality = response["evidence_quality"]
    
    # Validate score ranges
    required_scores = {
        "strength_score": (1, 5),
        "rigor_score": (1, 5),
        "relevance_score": (1, 5),
        "directness": (1, 3),
        "reproducibility_score": (1, 5),
        "composite_score": (1, 5)
    }
    
    for score_name, (min_val, max_val) in required_scores.items():
        if score_name not in quality:
            return None
        score = quality[score_name]
        if not isinstance(score, (int, float)) or score < min_val or score > max_val:
            return None
    
    # Validate study type
    if quality.get("study_type") not in ["experimental", "observational", "theoretical", "review", "opinion"]:
        return None
    
    # Validate confidence level
    if quality.get("confidence_level") not in ["high", "medium", "low"]:
        return None
    
    # Validate is_recent is boolean
    if not isinstance(quality.get("is_recent"), bool):
        return None
    
    return response


def meets_approval_criteria(quality: Dict) -> bool:
    """
    Check if evidence quality meets approval criteria.
    
    Criteria: composite_score ≥ 3.0 AND strength_score ≥ 3 AND relevance_score ≥ 3
    """
    composite = quality.get("composite_score", 0)
    strength = quality.get("strength_score", 0)
    relevance = quality.get("relevance_score", 0)
    
    return composite >= 3.0 and strength >= 3 and relevance >= 3


def migrate_existing_claims(history: Dict) -> Dict:
    """
    Add default scores to claims without evidence_quality for backward compatibility.
    
    This ensures existing approved claims have quality scores for analysis.
    """
    migrated_count = 0
    
    for filename, versions in history.items():
        for version in versions:
            claims = version.get('review', {}).get('Requirement(s)', [])
            for claim in claims:
                if 'evidence_quality' not in claim and claim.get('status') == 'approved':
                    # Assign default moderate scores for legacy approved claims
                    claim['evidence_quality'] = {
                        "strength_score": 3,
                        "strength_rationale": "Legacy claim (default score)",
                        "rigor_score": 3,
                        "study_type": "unknown",
                        "relevance_score": 3,
                        "relevance_notes": "Legacy claim",
                        "directness": 2,
                        "is_recent": False,
                        "reproducibility_score": 3,
                        "composite_score": 3.0,
                        "confidence_level": "medium"
                    }
                    migrated_count += 1
    
    if migrated_count > 0:
        logger.info(f"Migrated {migrated_count} legacy claims with default quality scores.")
    
    return history

# --- END ENHANCED EVIDENCE SCORING FUNCTIONS ---


# --- MAIN EXECUTION ---
def main():
    start_time = time.time()
    logger.info("\n" + "=" * 80)
    logger.info("JUDGE PIPELINE v2.0 (Uses Version History as Source of Truth)")
    logger.info("=" * 80)

    logger.info("\n=== INITIALIZING COMPONENTS ===")
    safe_print("\n=== INITIALIZING COMPONENTS ===")
    try:
        api_manager = APIManager()
    except Exception as init_e:
        logger.critical(f"Failed to initialize core components: {init_e}")
        safe_print(f"❌ Failed to initialize core components: {init_e}")
        return

    papers_folder_path = dra.find_papers_folder()
    if not papers_folder_path:
        logger.error("Could not find PAPERS_FOLDER. DRA will fail.")
        safe_print("❌ Could not find PAPERS_FOLDER. DRA will be skipped.")

    logger.info("\n=== LOADING DATA ===")
    safe_print("\n=== LOADING DATA ===")

    # NEW: Load ONLY from version history
    version_history = load_version_history(VERSION_HISTORY_FILE)
    pillar_definitions = load_pillar_definitions(DEFINITIONS_FILE)

    if not pillar_definitions:
        logger.critical("Missing pillar definitions. Exiting.")
        safe_print("❌ Missing pillar definitions. Exiting.")
        return
    
    # Migrate legacy claims to include default quality scores
    if version_history:
        version_history = migrate_existing_claims(version_history)
    
    if not version_history:
        logger.info("No version history found. Nothing to judge.")
        safe_print("⚖️ No version history found. All work is done.")
        return

    # Extract pending claims
    claims_to_judge = extract_pending_claims_from_history(version_history)
    
    if not claims_to_judge:
        logger.info("No pending claims found in version history.")
        safe_print("⚖️ No pending claims found. All work is done.")
        return
    
    logger.info(f"Found {len(claims_to_judge)} total claims pending judgment.")
    safe_print(f"⚖️ Found {len(claims_to_judge)} total claims pending judgment. The court is in session.")

    # --- PHASE 1: Initial Judgment (WITH BATCHING) ---
    logger.info("\n--- PHASE 1: Initial Judgment (Batched Processing) ---")
    safe_print("\n--- PHASE 1: Initial Judgment (Batched Processing) ---")

    init_approved_count = 0
    init_rejected_count = 0
    claims_for_dra_appeal = []
    all_judged_claims = []  # Track all claims for updating history
    
    # Split claims into batches
    claim_batches = process_claims_in_batches(claims_to_judge, API_CONFIG['CLAIM_BATCH_SIZE'])
    logger.info(f"Processing {len(claims_to_judge)} claims in {len(claim_batches)} batches of {API_CONFIG['CLAIM_BATCH_SIZE']}")
    safe_print(f"Processing {len(claims_to_judge)} claims in {len(claim_batches)} batches")

    for batch_num, claim_batch in enumerate(claim_batches, 1):
        logger.info(f"\n=== Processing Batch {batch_num}/{len(claim_batches)} ({len(claim_batch)} claims) ===")
        safe_print(f"\n=== Processing Batch {batch_num}/{len(claim_batches)} ({len(claim_batch)} claims) ===")
        
        for i, claim in enumerate(claim_batch, 1):
            overall_index = (batch_num - 1) * API_CONFIG['CLAIM_BATCH_SIZE'] + i
            filename = claim.get('_source_filename', 'N/A')
            claim_id_short = f"{filename[:15]}... ({claim['claim_id'][:6]})"
            logger.info(f"\n--- Judging Claim {overall_index}/{len(claims_to_judge)}: {claim_id_short} ---")
            safe_print(f"\n--- Judging Claim {overall_index}/{len(claims_to_judge)}: {claim_id_short} ---")

            try:
                sub_req_key = claim.get('sub_requirement') or claim.get('sub_requirement_key', 'N/A')
                pillar_key = claim.get('pillar', 'N/A')
                definition_text = find_robust_sub_requirement_text(sub_req_key)

                if not definition_text:
                    logger.error(f"  Could not find definition for claim. Rejecting.")
                    safe_print(f"  ❌ Could not find definition for '{sub_req_key}'. Rejecting.")
                    # Create default quality scores for rejected claim
                    ruling = {
                        "verdict": "rejected",
                        "judge_notes": f"Rejected. Could not find sub-requirement definition for '{sub_req_key}' in pillar file.",
                        "evidence_quality": {
                            "strength_score": 1,
                            "strength_rationale": "No definition found",
                            "rigor_score": 1,
                            "study_type": "unknown",
                            "relevance_score": 1,
                            "relevance_notes": "No definition to match against",
                            "directness": 1,
                            "is_recent": False,
                            "reproducibility_score": 1,
                            "composite_score": 1.0,
                            "confidence_level": "low"
                        }
                    }
                else:
                    # Use enhanced prompt with quality scoring
                    prompt = build_judge_prompt_enhanced(claim, definition_text)
                    logger.info(f"  Submitting claim to Judge AI...")
                    safe_print(f"  Submitting claim to Judge AI...")
                    response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
                    ruling = validate_judge_response_enhanced(response)

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
                    # Add evidence quality scores to claim
                    claim['evidence_quality'] = ruling.get('evidence_quality', {})
                    all_judged_claims.append(claim)

                    if ruling['verdict'] == 'approved':
                        logger.info(f"  VERDICT: APPROVED (Quality: {ruling.get('evidence_quality', {}).get('composite_score', 'N/A')})")
                        safe_print(f"  ✅ VERDICT: APPROVED (Quality: {ruling.get('evidence_quality', {}).get('composite_score', 'N/A')})")
                        init_approved_count += 1
                    else:
                        logger.info(f"  VERDICT: REJECTED (Pending DRA)")
                        safe_print(f"  ❌ VERDICT: REJECTED (Sending to DRA for appeal)")
                        init_rejected_count += 1
                        claims_for_dra_appeal.append(claim)
                else:
                    logger.error(f"  Judge AI returned invalid response. Claim will be re-judged next run.")
                    safe_print(f"  ⚠️ Judge AI returned invalid response. Skipping for next run.")
            except Exception as e:
                logger.critical(f"  CRITICAL UNHANDLED ERROR on claim {claim['claim_id']}: {e}")
                safe_print(f"  ❌ CRITICAL ERROR on claim. See log. Skipping.")
        
        # Log progress after each batch
        logger.info(f"\nBatch {batch_num} complete. Progress: {init_approved_count} approved, {init_rejected_count} rejected")
        safe_print(f"Batch {batch_num} complete. Progress: {init_approved_count} approved, {init_rejected_count} rejected")

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
        # Add source metadata
        for claim in new_claims_for_rejudgment:
            claim['_source_filename'] = claim.get('filename')
            claim['_source_type'] = 'dra_appeal'

    # --- PHASE 3: Final Judgment (on Appeals) (WITH BATCHING) ---
    logger.info("\n--- PHASE 3: Final Judgment (on Appeals) (Batched Processing) ---")
    safe_print("\n--- PHASE 3: Final Judgment (on Appeals) (Batched Processing) ---")

    dra_approved_count = 0
    dra_rejected_count = 0

    if not new_claims_for_rejudgment:
        logger.info("DRA did not re-submit any new claims.")
        safe_print("⚖️ DRA did not re-submit any new claims.")
    else:
        logger.info(f"DRA re-submitted {len(new_claims_for_rejudgment)} new claims. Starting final judgment...")
        safe_print(f"⚖️ DRA re-submitted {len(new_claims_for_rejudgment)} new claims. Starting final judgment...")

        # Split DRA claims into batches
        dra_claim_batches = process_claims_in_batches(new_claims_for_rejudgment, API_CONFIG['CLAIM_BATCH_SIZE'])
        logger.info(f"Processing {len(new_claims_for_rejudgment)} DRA claims in {len(dra_claim_batches)} batches")
        
        for batch_num, claim_batch in enumerate(dra_claim_batches, 1):
            logger.info(f"\n=== Processing DRA Batch {batch_num}/{len(dra_claim_batches)} ({len(claim_batch)} claims) ===")
            safe_print(f"\n=== Processing DRA Batch {batch_num}/{len(dra_claim_batches)} ({len(claim_batch)} claims) ===")
            
            for i, new_claim in enumerate(claim_batch, 1):
                overall_index = (batch_num - 1) * API_CONFIG['CLAIM_BATCH_SIZE'] + i
                filename = new_claim.get('filename', 'N/A')
                claim_id_short = f"{filename[:15]}... ({new_claim['claim_id'][:6]})"
                logger.info(f"\n--- Re-Judging Claim {overall_index}/{len(new_claims_for_rejudgment)}: {claim_id_short} ---")
                safe_print(f"\n--- Re-Judging Claim {overall_index}/{len(new_claims_for_rejudgment)}: {claim_id_short} ---")

                try:
                    sub_req_key = new_claim.get('sub_requirement', 'N/A')
                    pillar_key = new_claim.get('pillar', 'N/A')
                    definition_text = find_robust_sub_requirement_text(sub_req_key)

                    if not definition_text:
                        logger.error(f"  Could not find definition for DRA claim. Rejecting.")
                        safe_print(f"  ❌ Could not find definition for '{sub_req_key}'. Rejecting.")
                        # Create default quality scores for rejected claim
                        ruling = {
                            "verdict": "rejected",
                            "judge_notes": f"Rejected. (DRA Appeal) Could not find sub-requirement definition for '{sub_req_key}'.",
                            "evidence_quality": {
                                "strength_score": 1,
                                "strength_rationale": "No definition found",
                                "rigor_score": 1,
                                "study_type": "unknown",
                                "relevance_score": 1,
                                "relevance_notes": "No definition to match against",
                                "directness": 1,
                                "is_recent": False,
                                "reproducibility_score": 1,
                                "composite_score": 1.0,
                                "confidence_level": "low"
                            }
                        }
                    else:
                        # Use enhanced prompt with quality scoring
                        prompt = build_judge_prompt_enhanced(new_claim, definition_text)
                        logger.info(f"  Submitting DRA claim to Judge AI...")
                        safe_print(f"  Submitting DRA claim to Judge AI...")
                        response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
                        ruling = validate_judge_response_enhanced(response)

                    if ruling:
                        new_claim['status'] = ruling['verdict']
                        new_claim['judge_notes'] = ruling['judge_notes']
                        new_claim['judge_timestamp'] = datetime.now().isoformat()
                        # Add evidence quality scores to claim
                        new_claim['evidence_quality'] = ruling.get('evidence_quality', {})

                        if ruling['verdict'] == 'approved':
                            logger.info(f"  VERDICT (Appeal): APPROVED (Quality: {ruling.get('evidence_quality', {}).get('composite_score', 'N/A')})")
                            safe_print(f"  ✅ VERDICT (Appeal): APPROVED (Quality: {ruling.get('evidence_quality', {}).get('composite_score', 'N/A')})")
                            dra_approved_count += 1
                        else:
                            logger.info(f"  VERDICT (Appeal): REJECTED")
                            safe_print(f"  ❌ VERDICT (Appeal): REJECTED")
                            dra_rejected_count += 1

                        all_judged_claims.append(new_claim)
                    else:
                        logger.error(f"  Judge AI returned invalid response for DRA claim. Claim is lost.")
                        safe_print(f"  ⚠️ Judge AI returned invalid response for DRA claim. Skipping.")

                except Exception as e:
                    logger.critical(f"  CRITICAL UNHANDLED ERROR on DRA claim {new_claim['claim_id']}: {e}")
                    safe_print(f"  ❌ CRITICAL ERROR on DRA claim. See log. Skipping.")
            
            # Log progress after each DRA batch
            logger.info(f"\nDRA Batch {batch_num} complete. Progress: {dra_approved_count} approved, {dra_rejected_count} rejected")
            safe_print(f"DRA Batch {batch_num} complete. Progress: {dra_approved_count} approved, {dra_rejected_count} rejected")

    # --- PHASE 4: Save All Results to Version History ---
    logger.info("\n--- PHASE 4: Saving Results to Version History ---")
    safe_print("\n--- PHASE 4: Saving Results to Version History ---")

    # Update existing claims
    version_history = update_claims_in_history(version_history, all_judged_claims)
    
    # Add new DRA claims
    if new_claims_for_rejudgment:
        version_history = add_new_claims_to_history(version_history, new_claims_for_rejudgment)

    # Save to version history ONLY
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
    safe_print("\n  📝 Version history updated:")
    safe_print(f"    - {VERSION_HISTORY_FILE}")
    safe_print("\n  ⚠️  Run sync_history_to_db.py to update CSV database.")

    end_time = time.time()
    logger.info(f"Total time taken: {end_time - start_time:.2f} seconds.")
    safe_print(f"Total time taken: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()