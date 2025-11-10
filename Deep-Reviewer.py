"""
Deep Reviewer
Version: 2.0 (Task Card #4: Migrated to Version History)
Date: 2025-11-10

This script reads the gap analysis from the Orchestrator and the main
neuromorphic database. It re-analyzes promising papers to find specific
text chunks ("Deep Coverage") that address identified research gaps.
These claims are now stored in review_version_history.json (source of truth).
"""

import os
import sys
import json
import csv
import pypdf
import pdfplumber
import time
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from google import genai
from google.genai import types
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
import pickle
from sentence_transformers import SentenceTransformer
import warnings
from pathlib import Path

# --- CONFIGURATION ---
load_dotenv()

# 1. Input Files
# From Journal Reviewer
PAPERS_FOLDER = r'C:\Users\jpcol\OneDrive\Documents\Doctorate\Research\Literature-Review'
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'
# From Orchestrator
GAP_REPORT_FILE = 'gap_analysis_output/gap_analysis_report.json'
DEEP_REVIEW_DIRECTIONS_FILE = 'gap_analysis_output/deep_review_directions.json'

# 2. Input/Output File (This script's state)
# DEPRECATED: DEEP_COVERAGE_DB_FILE = 'deep_coverage_database.json'
# Now using version history as single source of truth (Task Card #4)
VERSION_HISTORY_FILE = 'review_version_history.json'

# 3. Path/API Config (Copied from Journal-Reviewer)
ALTERNATIVE_PATHS = [
    r'C:\Users\jpcol\Documents\Doctorate\Research\Literature-Review',
    r'C:\Users\jpcol\OneDrive\Documents\Research\Literature-Review',
    r'.\Literature-Review',
    r'..\Literature-Review',
]
CACHE_DIR = 'deep_reviewer_cache'
API_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "API_CALLS_PER_MINUTE": 60,
}
SUPPORTED_EXTENSIONS = ('.pdf', '.html', '.txt', '.HTML', '.PDF', '.TXT')
MIN_TEXT_LENGTH = 500  # For TextExtractor

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.file_download")
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# Fix Unicode issues on Windows
if sys.platform == "win32":
    import locale

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    if sys.stderr.encoding != 'utf-8':
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass


# --- Logging Setup (Copied from Journal-Reviewer) ---
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
file_handler = logging.FileHandler('deep_reviewer.log', encoding='utf-8')
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


# --- DEPRECATED: DeepCoverageEntry dataclass ---
# This has been replaced with direct dictionary format for version history
# See create_requirement_entry() function for the new format


# --- APIManager CLASS (Copied from Journal-Reviewer v3.1) ---
class APIManager:
    """Manages API calls with rate limiting, caching, and retry logic"""

    def __init__(self):
        self.cache = {}
        self.last_call_time = 0
        self.calls_this_minute = 0
        self.minute_start = time.time()

        try:
            self.client = genai.Client()
            thinking_config = types.ThinkingConfig(thinking_budget=1)

            self.json_generation_config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=1.0,
                top_k=1,
                max_output_tokens=16384,
                response_mime_type="application/json",
                thinking_config=thinking_config
            )

            logger.info(f"[SUCCESS] Gemini Client (google-ai SDK) initialized (Thinking Enabled.")
            safe_print(f"✅ Gemini Client initialized successfully (Thinking Enabled).")
        except Exception as e:
            logger.critical(f"[ERROR] Critical Error initializing Gemini Client: {e}")
            safe_print(f"❌ Critical Error initializing Gemini Client: {e}")
            raise

    def rate_limit(self):
        """Implement rate limiting"""
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

    def cached_api_call(self, prompt: str, use_cache: bool = True) -> Optional[Any]:
        """Make API call with caching and retry logic"""
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
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=self.json_generation_config
                )

                response_text = response.text
                result = json.loads(response_text)
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


# --- TextExtractor CLASS (Copied from Journal-Reviewer v3.1) ---
# This is VITAL for re-reading the original paper files
class TextExtractor:
    """Robust text extraction from multiple file formats"""

    @staticmethod
    def extract_with_pypdf(filepath: str) -> Tuple[str, List[str]]:
        """Extract text using pypdf, returning full text and page-wise text"""
        full_text = ""
        pages_text = []
        try:
            with open(filepath, 'rb') as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                if page_count == 0:
                    return "", []

                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            page_text_with_header = f"\n--- Page {i + 1} ---\n{page_text}\n"
                            full_text += page_text_with_header
                            pages_text.append(page_text_with_header)
                        else:
                            pages_text.append(f"\n--- Page {i + 1} ---\n[No text extracted]\n")
                    except Exception:
                        pages_text.append(f"\n--- Page {i + 1} ---\n[Error extracting page]\n")
                return full_text, pages_text
        except Exception as e:
            logger.error(f"pypdf extraction failed for {os.path.basename(filepath)}: {e}")
            return "", []

    @staticmethod
    def extract_with_pdfplumber(filepath: str) -> Tuple[str, List[str]]:
        """Extract text using pdfplumber, returning full text and page-wise text"""
        full_text = ""
        pages_text = []
        try:
            with pdfplumber.open(filepath) as pdf:
                page_count = len(pdf.pages)
                if page_count == 0:
                    return "", []

                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text(x_tolerance=1, y_tolerance=1)
                        if page_text:
                            page_text_with_header = f"\n--- Page {i + 1} ---\n{page_text}\n"
                            full_text += page_text_with_header
                            pages_text.append(page_text_with_header)
                        else:
                            pages_text.append(f"\n--- Page {i + 1} ---\n[No text extracted]\n")
                    except Exception:
                        pages_text.append(f"\n--- Page {i + 1} ---\n[Error extracting page]\n")
                return full_text, pages_text
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {os.path.basename(filepath)}: {e}")
            return "", []

    @staticmethod
    def extract_from_html(filepath: str) -> Tuple[str, List[str]]:
        """Extract text from HTML files"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    if tag: tag.decompose()
                main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find(
                    'div', class_='content') or soup.body
                if main_content:
                    text = main_content.get_text(separator='\n', strip=True)
                else:
                    text = soup.get_text(separator='\n', strip=True)

                # HTMLs don't have pages, so return as one page
                pages_text = [f"\n--- Page 1 ---\n{text}\n"]
                return text, pages_text
        except Exception as e:
            logger.error(f"HTML extraction failed for {os.path.basename(filepath)}: {e}")
            return "", []

    @classmethod
    def robust_text_extraction(cls, filepath: str) -> Tuple[str, List[str]]:
        """Multi-method extraction. Returns full text and list of text per page."""
        logger.info(f"Deep Review: Extracting text from: {os.path.basename(filepath)}")
        safe_print(f"📄 Deep Review: Extracting text from: {os.path.basename(filepath)}")

        full_text, pages_text = "", []
        file_ext = os.path.splitext(filepath)[1].lower()

        if file_ext == '.html':
            full_text, pages_text = cls.extract_from_html(filepath)
        elif file_ext == '.pdf':
            # Try pdfplumber first, fallback to pypdf
            plumber_text, plumber_pages = cls.extract_with_pdfplumber(filepath)
            pypdf_text, pypdf_pages = cls.extract_with_pypdf(filepath)

            if len(plumber_text) >= len(pypdf_text):
                full_text, pages_text = plumber_text, plumber_pages
            else:
                full_text, pages_text = pypdf_text, pypdf_pages
        elif file_ext == '.txt':
            try:
                encodings_to_try = ['utf-8', 'cp1252', 'latin-1']
                for enc in encodings_to_try:
                    try:
                        with open(filepath, 'r', encoding=enc) as f:
                            full_text = f.read()
                        pages_text = [f"\n--- Page 1 ---\n{full_text}\n"]
                        break
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                logger.error(f"Text file reading failed: {e}")

        return full_text, pages_text


# --- Path Diagnostic Functions (Copied from Journal-Reviewer v3.1) ---
# Needed to find the PAPERS_FOLDER
def find_papers_folder():
    """Find the papers folder by checking multiple locations"""
    if os.path.exists(PAPERS_FOLDER) and os.path.isdir(PAPERS_FOLDER):
        logger.info(f"Using primary PAPERS_FOLDER: {PAPERS_FOLDER}")
        return PAPERS_FOLDER

    for alt_path in ALTERNATIVE_PATHS:
        abs_path = os.path.abspath(alt_path)
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            logger.info(f"Found papers folder at alternative location: {abs_path}")
            return abs_path

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.path.abspath('.')

    possible_paths = [
        os.path.join(script_dir, 'Literature-Review'),
        os.path.join(script_dir, '..', 'Literature-Review'),
        os.path.join(script_dir, 'Research', 'Literature-Review'),
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            logger.info(f"Found papers folder relative to script: {abs_path}")
            return abs_path

    logger.error("Could not find papers folder in any specified location.")
    return None


def find_paper_filepath(filename: str, papers_folder: str) -> Optional[str]:
    """Find the full file path for a given filename."""
    for root, dirs, files in os.walk(papers_folder):
        if filename in files:
            return os.path.join(root, filename)
    logger.warning(f"Could not find file: {filename} in {papers_folder}")
    return None


# --- DATA LOADING FUNCTIONS ---

def load_gap_report(filepath: str) -> Dict:
    """Loads the Orchestrator's gap analysis report."""
    if not os.path.exists(filepath):
        logger.error(f"Gap report not found: {filepath}")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading gap report: {e}")
        return {}


def load_research_db(filepath: str) -> Optional[pd.DataFrame]:
    """Loads the main neuromorphic database."""
    if not os.path.exists(filepath):
        logger.error(f"Research DB not found: {filepath}")
        return None
    try:
        return pd.read_csv(filepath, encoding='utf-8')
    except Exception as e:
        logger.error(f"Error loading research DB: {e}")
        return None


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


def get_all_claims_from_history(version_history: Dict) -> List[Dict]:
    """
    Extract all claims from version history into a flat list for comparison.
    Returns a list of claims with 'filename' field added.
    """
    all_claims = []
    for filename, versions in version_history.items():
        if not versions:
            continue
        # Get latest version
        latest_version = versions[-1]
        review = latest_version.get('review', {})
        requirements = review.get('Requirement(s)', [])
        
        for req in requirements:
            # Add filename to claim for context
            claim_with_file = req.copy()
            claim_with_file['filename'] = filename
            all_claims.append(claim_with_file)
    
    return all_claims


def load_directions(filepath: str) -> Dict:
    """Loads the directions from the Orchestrator."""
    if not os.path.exists(filepath):
        logger.info("No deep review directions file found.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            directions = json.load(f)
            logger.info(f"Loaded {len(directions)} sub-requirements from directions file.")
            return directions
    except Exception as e:
        logger.error(f"Error loading directions file: {e}")
        return {}


def clear_directions_file(filepath: str):
    """Clears the directions file after processing."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logger.info(f"Cleared directions file: {filepath}")
    except Exception as e:
        logger.error(f"Error clearing directions file: {e}")


# --- CORE LOGIC FUNCTIONS ---

def find_gaps_to_review(gap_report: Dict, directions: Dict) -> List[Dict]:
    """
    Identifies all sub-requirements that need deep review.
    Uses directions if provided, otherwise finds all gaps < 100%.
    """
    gaps_to_review = []

    # Priority 1: Use directions from the Orchestrator
    if directions:
        logger.info("Processing based on Orchestrator directions.")
        for sub_req_key, pillar_info in directions.items():
            pillar_name = pillar_info.get("pillar")
            req_key = pillar_info.get("requirement_key")

            if not all([pillar_name, req_key]):
                logger.warning(f"Skipping incomplete direction: {sub_req_key}")
                continue

            try:
                # Get gap text and contributing papers from the main gap report
                gap_data = gap_report[pillar_name]['analysis'][req_key][sub_req_key]
                gaps_to_review.append({
                    "pillar": pillar_name,
                    "requirement_key": req_key,
                    "sub_requirement_key": sub_req_key,
                    "gap_analysis": gap_data.get('gap_analysis', 'N/A'),
                    "contributing_papers": [p.get("filename") for p in gap_data.get('contributing_papers', [])]
                })
            except KeyError:
                logger.error(f"Could not find data for directed sub-req: {sub_req_key}")
        return gaps_to_review

    # Priority 2: No directions, so find all gaps < 100%
    logger.info("No directions found. Scanning all gaps with < 100% completeness.")
    for pillar_name, pillar_data in gap_report.items():
        for req_key, req_data in pillar_data.get('analysis', {}).items():
            for sub_req_key, sub_req_data in req_data.items():
                if sub_req_data.get("completeness_percent", 100) < 100:
                    gaps_to_review.append({
                        "pillar": pillar_name,
                        "requirement_key": req_key,
                        "sub_requirement_key": sub_req_key,
                        "gap_analysis": sub_req_data.get('gap_analysis', 'N/A'),
                        "contributing_papers": [p.get("filename") for p in sub_req_data.get('contributing_papers', [])]
                    })

    logger.info(f"Found {len(gaps_to_review)} total gaps to review.")
    return gaps_to_review


def find_promising_papers(
        gap: Dict,
        research_db: pd.DataFrame,
        all_claims: List[Dict]
) -> List[Dict]:
    """
    Finds papers that are likely to fill the gap.
    Starts with 'contributing_papers' from the gap report.
    Filters out papers that already have an 'approved' claim for this gap.
    
    Args:
        gap: Gap information dict
        research_db: Main research database
        all_claims: List of all claims from version history
    """
    paper_filenames = gap.get("contributing_papers", [])
    if not paper_filenames:
        # Fallback: Find all highly relevant papers from the main DB
        logger.info(f"No contributing papers listed for gap. Searching main DB.")
        relevant_rows = research_db[
            (research_db['SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE'] > 70)
        ]
        paper_filenames = relevant_rows['FILENAME'].tolist()

    # Get set of papers that already have an 'approved' claim for this sub-req
    approved_papers = {
        entry['filename'] for entry in all_claims
        if entry.get('sub_requirement') == gap['sub_requirement_key']
           and entry.get('status') == 'approved'
    }

    # Get set of papers that have a 'pending' claim (to avoid duplicates)
    pending_papers = {
        entry['filename'] for entry in all_claims
        if entry.get('sub_requirement') == gap['sub_requirement_key']
           and entry.get('status') == 'pending_judge_review'
    }

    promising_paper_info = []
    for filename in paper_filenames:
        if filename in approved_papers:
            logger.debug(f"Skipping {filename}: already has 'approved' claim for this gap.")
            continue

        if filename in pending_papers:
            logger.debug(f"Skipping {filename}: already has 'pending' claim for this gap.")
            continue

        paper_row = research_db[research_db['FILENAME'] == filename]
        if not paper_row.empty:
            promising_paper_info.append(paper_row.iloc[0].to_dict())
        else:
            logger.warning(f"Could not find paper info for {filename} in research DB.")

    return promising_paper_info


def build_deep_review_prompt(
        gap: Dict,
        paper_info: Dict,
        paper_pages_text: List[str],
        existing_claims: List[Dict]
) -> str:
    """Builds the comprehensive prompt for the AI Deep Reviewer."""

    existing_claims_str = "None."
    if existing_claims:
        existing_claims_str = "\n".join(
            f"- {claim['claim_summary']} (Status: {claim['status']})"
            for claim in existing_claims
        )

    # We send the text page by page to make it easier for the AI
    # to find page numbers and process context.
    full_text_str = "\n".join(paper_pages_text)

    return f"""
You are a "Deep Reviewer" AI agent. Your task is to re-read a paper's full text to find specific, new evidence for a known research gap.

--- CORE RESEARCH CONTEXT ---
Our core research topic is: "The mapping of human brain functions to machine learning frameworks, specifically in the areas of skill acquisition, memory consolidation, and stimulus-response, with emphasis on neuromorphic computing architectures."

--- THE GAP TO FILL ---
Pillar: {gap['pillar']}
Requirement: {gap['requirement_key']}
Sub-Requirement (Target): {gap['sub_requirement_key']}
Current Gap Analysis: "{gap['gap_analysis']}"

--- THE PAPER TO ANALYZE ---
Title: {paper_info.get('TITLE', 'N/A')}
Filename: {paper_info.get('FILENAME', 'N/A')}
Existing Major Findings: {paper_info.get('MAJOR_FINDINGS', 'N/A')}

--- EXISTING CLAIMS FOR THIS PAPER (DO NOT REPEAT) ---
You (or another reviewer) have already made the following claims about this paper related to this sub-requirement. DO NOT find the same evidence again. Find *new* evidence.
{existing_claims_str}

--- YOUR TASK ---
Scan the *entire* full text of the paper provided below. Find up to 3 *new* and *distinct* text chunks (1-5 sentences) that *directly* contribute to fulfilling the **Sub-Requirement (Target)**.

For each chunk you find:
1.  **Extract the text:** Quote the text *exactly* as it appears.
2.  **Summarize the claim:** Write a 1-sentence summary of *how* this chunk helps fill the gap.
3.  **Estimate page:** Find the page number (e.g., "--- Page 5 ---") immediately preceding the text.
4.  **Confidence:** Rate your confidence (0.0 to 1.0) that this chunk is *new* and *relevant* to the gap.

--- OUTPUT FORMAT (JSON ONLY) ---
Return a *single* JSON object. The object should contain one key, "new_claims", which is a list of claim objects.
If no new evidence is found, return {{"new_claims": []}}.

Example:
{{
  "new_claims": [
    {{
      "claim_summary": "This chunk provides a specific algorithm for synaptic scaling, which directly addresses the gap.",
      "evidence_chunk": "Our proposed model, outlined in Eq. 4, implements a homeostatic synaptic scaling mechanism...",
      "page_number": 5,
      "reviewer_confidence": 0.95
    }},
    {{
      "claim_summary": "This result table validates the algorithm's energy efficiency, another aspect of the gap.",
      "evidence_chunk": "As shown in Table 3, our SNN model achieves 98% accuracy on MNIST while consuming only 2.1 mJ per inference.",
      "page_number": 7,
      "reviewer_confidence": 0.8
    }}
  ]
}}
--- START FULL PAPER TEXT (PAGE-BY-PAGE) ---
{full_text_str}
--- END FULL PAPER TEXT ---
"""


def create_requirement_entry(
        claim_data: Dict,
        paper_info: Dict,
        gap: Dict
) -> Dict:
    """
    Creates a new requirement entry for version history from AI output.
    Uses the version history Requirement(s) format with extended fields.
    """
    filename = paper_info.get('FILENAME', 'N/A')
    sub_req = gap.get('sub_requirement_key', 'N/A')
    chunk = claim_data.get('evidence_chunk', '')

    # Create a unique, repeatable ID
    claim_hash = hashlib.md5(f"{filename}{sub_req}{chunk}".encode('utf-8')).hexdigest()

    return {
        "claim_id": claim_hash,
        "pillar": gap.get('pillar', 'N/A'),
        "sub_requirement": sub_req,
        "evidence_chunk": chunk,
        "claim_summary": claim_data.get('claim_summary', 'No summary provided.'),
        "status": 'pending_judge_review',
        # Extended fields from Deep Reviewer
        "requirement_key": gap.get('requirement_key', 'N/A'),
        "page_number": claim_data.get('page_number', 0),
        "reviewer_confidence": claim_data.get('reviewer_confidence', 0.5),
        "judge_notes": "",
        "review_timestamp": datetime.now().isoformat(),
        "source": "deep_reviewer"
    }


def add_claim_to_version_history(
        version_history: Dict,
        filename: str,
        claim: Dict
) -> None:
    """
    Add a claim to the version history for a specific file.
    Creates a new version entry or updates the latest one.
    """
    timestamp = datetime.now().isoformat()
    
    # Ensure file exists in version history
    if filename not in version_history:
        logger.info(f"Creating new version history entry for {filename}")
        version_history[filename] = []
    
    # Get or create latest version
    if not version_history[filename]:
        # Create new version
        version_history[filename].append({
            "timestamp": timestamp,
            "review": {
                "FILENAME": filename,
                "Requirement(s)": []
            },
            "changes": {
                "status": "deep_reviewer_claims"
            }
        })
    
    latest_version = version_history[filename][-1]
    
    # Ensure Requirement(s) field exists
    if "Requirement(s)" not in latest_version["review"]:
        latest_version["review"]["Requirement(s)"] = []
    
    # Add the claim
    latest_version["review"]["Requirement(s)"].append(claim)
    logger.debug(f"Added claim {claim['claim_id']} to {filename}")


# --- MAIN EXECUTION ---
def main():
    start_time = time.time()
    logger.info("\n" + "=" * 80)
    logger.info("DEEP REVIEWER PIPELINE v1.0")
    logger.info("=" * 80)

    papers_folder_path = find_papers_folder()
    if not papers_folder_path:
        safe_print("❌ Could not find PAPERS_FOLDER. Exiting.")
        return

    logger.info("\n=== INITIALIZING COMPONENTS ===")
    safe_print("\n=== INITIALIZING COMPONENTS ===")
    try:
        api_manager = APIManager()
        text_extractor = TextExtractor()
    except Exception as init_e:
        logger.critical(f"Failed to initialize core components: {init_e}")
        safe_print(f"❌ Failed to initialize core components: {init_e}")
        return

    logger.info("\n=== LOADING DATABASES ===")
    safe_print("\n=== LOADING DATABASES ===")
    gap_report = load_gap_report(GAP_REPORT_FILE)
    research_db = load_research_db(RESEARCH_DB_FILE)
    version_history = load_version_history(VERSION_HISTORY_FILE)
    directions = load_directions(DEEP_REVIEW_DIRECTIONS_FILE)

    if not gap_report or research_db is None:
        logger.critical("Missing critical input files (Gap Report or Research DB). Exiting.")
        safe_print("❌ Missing critical input files. Exiting.")
        return

    logger.info("\n=== FINDING GAPS TO REVIEW ===")
    safe_print("\n=== FINDING GAPS TO REVIEW ===")
    gaps_to_review = find_gaps_to_review(gap_report, directions)

    if not gaps_to_review:
        logger.info("No gaps to review. (Either no directions or all gaps >= 100%).")
        safe_print("📭 No gaps to review. Pipeline complete.")
        clear_directions_file(DEEP_REVIEW_DIRECTIONS_FILE)  # Clear directions if they were processed
        return

    logger.info(f"Found {len(gaps_to_review)} sub-requirement gaps to analyze.")
    safe_print(f"Found {len(gaps_to_review)} sub-requirement gaps to analyze.")

    # Extract all claims from version history for comparison
    all_claims = get_all_claims_from_history(version_history)
    logger.info(f"Found {len(all_claims)} existing claims in version history")
    
    new_claims_found = 0
    existing_claim_ids = {claim.get('claim_id') for claim in all_claims}

    for i, gap in enumerate(gaps_to_review, 1):
        gap_id = f"{gap['pillar'].split(':')[0]} / {gap['sub_requirement_key'].split(':')[0]}"
        logger.info(f"\n--- Processing Gap {i}/{len(gaps_to_review)}: {gap_id} ---")
        safe_print(f"\n--- Processing Gap {i}/{len(gaps_to_review)}: {gap_id} ---")

        promising_papers = find_promising_papers(gap, research_db, all_claims)

        if not promising_papers:
            logger.info(f"No promising papers found for this gap (all may be 'approved' or 'pending').")
            safe_print(f"  No new papers to review for this gap.")
            continue

        logger.info(f"  Found {len(promising_papers)} promising papers to scan.")

        for paper_info in promising_papers:
            filename = paper_info.get('FILENAME', 'N/A')
            logger.info(f"  Scanning paper: {filename}")
            safe_print(f"  Scanning paper: {filename}")

            try:
                filepath = find_paper_filepath(filename, papers_folder_path)
                if not filepath:
                    logger.warning(f"    Could not find file {filename}. Skipping.")
                    safe_print(f"    ❌ Could not find file {filename}. Skipping.")
                    continue

                # Re-extract the full text, page by page
                full_text, pages_text = text_extractor.robust_text_extraction(filepath)

                if not full_text or len(full_text) < MIN_TEXT_LENGTH:
                    logger.warning(f"    Text extraction failed or text too short for {filename}. Skipping.")
                    safe_print(f"    ❌ Text extraction failed for {filename}. Skipping.")
                    continue

                # Find all existing claims for this specific paper+gap
                existing_claims_for_paper = [
                    claim for claim in all_claims
                    if claim.get('filename') == filename
                       and claim.get('sub_requirement') == gap['sub_requirement_key']
                ]

                prompt = build_deep_review_prompt(gap, paper_info, pages_text, existing_claims_for_paper)

                # Use cache=False to ensure we re-analyze for *new* claims
                # if the context (e.g., existing claims) has changed.
                ai_response = api_manager.cached_api_call(prompt, use_cache=False)

                if ai_response and "new_claims" in ai_response:
                    new_claims_data = ai_response["new_claims"]
                    if not new_claims_data:
                        logger.info(f"    No *new* evidence found in {filename}.")
                        safe_print(f"    No *new* evidence found.")
                        continue

                    for claim_data in new_claims_data:
                        new_requirement = create_requirement_entry(claim_data, paper_info, gap)

                        if new_requirement['claim_id'] not in existing_claim_ids:
                            # Add claim to version history
                            add_claim_to_version_history(version_history, filename, new_requirement)
                            existing_claim_ids.add(new_requirement['claim_id'])
                            new_claims_found += 1
                            logger.info(f"    ✅ Found new claim in {filename}!")
                            safe_print(
                                f"    ✅ Found new claim! (Confidence: {new_requirement['reviewer_confidence']:.1f})")
                        else:
                            logger.warning(f"    Duplicate claim ID detected. Skipping.")

                else:
                    logger.error(f"    API call failed or returned invalid JSON for {filename}.")
                    safe_print(f"    ❌ API call failed for {filename}.")

            except Exception as e:
                logger.critical(f"    CRITICAL UNHANDLED ERROR on file {filename}: {e}")
                safe_print(f"    ❌ CRITICAL ERROR on {filename}. See log. Skipping.")

    logger.info("\n" + "=" * 80)
    logger.info("DEEP REVIEW COMPLETE")

    if new_claims_found > 0:
        save_version_history(VERSION_HISTORY_FILE, version_history)
        logger.info(f"Found and saved {new_claims_found} new claims.")
        safe_print(f"✅ Found and saved {new_claims_found} new claims to `{VERSION_HISTORY_FILE}`")
        safe_print("  Ready for 'Judge' script review.")
        safe_print(f"  Note: Run sync_history_to_db.py to update the CSV database.")
    else:
        logger.info("No new claims were found in this run.")
        safe_print("✅ No new claims were found in this run.")

    # Clear directions file *after* processing is complete
    if directions:
        clear_directions_file(DEEP_REVIEW_DIRECTIONS_FILE)

    end_time = time.time()
    logger.info(f"Total time taken: {end_time - start_time:.2f} seconds.")
    safe_print(f"Total time taken: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()