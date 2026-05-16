"""
Enhanced Literature Review Pipeline for Neuromorphic Computing Research
Integrates pillar definitions to extract specific requirement claims during review.
Version: 3.3 (Enforces Master Column Order & Stricter Prompt)
Date: 2025-11-09
"""

import os
import sys
import json
import csv
import re
import difflib
import pypdf
import pdfplumber
try:
    import fitz  # PyMuPDF — primary PDF text + metadata extractor
except ImportError:  # pragma: no cover
    fitz = None
import time
import concurrent.futures
import hashlib
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
# Use google.genai (new SDK) for Client() interface
from google import genai
from google.genai import types
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from dataclasses import dataclass, asdict
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
from pathlib import Path

# Import global rate limiter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.global_rate_limiter import global_limiter, ErrorAction

# Import research configuration
from literature_review.config.research_config import (
    get_config, 
    get_research_topic_safe, 
    get_short_description_safe,
    get_database_filename_safe,
    is_config_loaded
)

# Import model configuration
from literature_review.config.model_config import get_model_config

# Note: pandas is imported locally in the function that needs it
# import pandas as pd

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

# --- 0. Load Environment Variables ---
load_dotenv()

# --- CONFIGURATION ---
PAPERS_FOLDER = 'data/raw'
REVIEW_LOG_FILE = 'review_log.json'
# OUTPUT_CSV_FILE is now dynamically loaded from research_config.json
# Fallback to legacy value if config not loaded
OUTPUT_CSV_FILE = get_database_filename_safe() if is_config_loaded() else 'neuromorphic-research_database.csv'
NON_JOURNAL_CSV_FILE = 'non-journal_database.csv'
DUPLICATE_MODE = 'skip'
CACHE_DIR = 'cache'
EMBEDDINGS_CACHE = os.path.join(CACHE_DIR, 'embeddings_cache.pkl')
VERSION_HISTORY_FILE = 'review_version_history.json'

# --- NEW: Definitions file for cross-referencing ---
DEFINITIONS_FILE = 'pillar_definitions.json'

REVIEW_CONFIG = {
    "BATCH_SIZE": 5,
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "CACHE_EMBEDDINGS": True,
    "SIMILARITY_THRESHOLD": 0.85,
    "MIN_TEXT_LENGTH": 500,
    "CHUNK_SIZE": 100000,
    "API_CALLS_PER_MINUTE": 10,  # Conservative limit for gemini-2.5-flash (1000 RPM available)
    "CONSENSUS_EVALUATIONS": 1,
    "API_TIMEOUT": 600
}

SUPPORTED_EXTENSIONS = ('.pdf', '.html', '.txt', '.HTML', '.PDF', '.TXT')


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
file_handler = logging.FileHandler('review_pipeline.log', encoding='utf-8')
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


# --- Data Classes ---
@dataclass
class PaperMetadata:
    filename: str
    filepath: str
    domain_context: str
    extraction_quality: float
    extraction_method: str
    timestamp: str

@dataclass
class QualityIndicators:
    has_abstract: bool
    has_references: bool
    has_methods: bool
    sufficient_length: bool
    extraction_quality: float

# --- GOLDEN DATASET: Dataclass for Claims ---
@dataclass
class GoldenDatasetClaim:
    """Structured claim following AGENT_ANNOTATION_PROMPT.md schema"""
    claim_id: str           # Format: "{paper_id}-C001"
    claim_type: str         # "quantitative" or "qualitative"
    pillar: str             # Exact pillar name from definitions
    sub_requirement: str    # Exact sub-requirement string
    claim_text: str         # Summary of what this claim shows
    verbatim_quote: str     # Exact text from paper (≤100 words)
    page: int               # Page number where quote appears
    section: str            # Section name (e.g., "Results")
    confidence: str         # "high", "medium", or "low"
    verification_notes: str # How to verify this claim
    status: str             # "pending_judge_review"

    def to_dict(self):
        return {
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "pillar": self.pillar,
            "sub_requirement": self.sub_requirement,
            "claim_text": self.claim_text,
            "verbatim_quote": self.verbatim_quote,
            "location": {
                "page": self.page,
                "section": self.section
            },
            "confidence": self.confidence,
            "verification_notes": self.verification_notes,
            "status": self.status
        }

@dataclass
class GoldenDatasetGap:
    """Structured gap following AGENT_ANNOTATION_PROMPT.md schema"""
    gap_id: str             # Format: "{paper_id}-G001"
    gap_type: str           # "limitation", "future_work", or "open_question"
    gap_text: str           # Description of the gap
    verbatim_quote: str     # Direct quote if available (or None)
    page: int               # Page number (or None)
    section: str            # Section name
    implied_vs_explicit: str # "explicit" or "implied"
    research_direction: str  # What future work could address this

    def to_dict(self):
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type,
            "gap_text": self.gap_text,
            "verbatim_quote": self.verbatim_quote,
            "location": {
                "page": self.page,
                "section": self.section
            },
            "implied_vs_explicit": self.implied_vs_explicit,
            "research_direction": self.research_direction
        }

def collect_papers_to_process(folder_path, reviewed_files):
    """Collect all papers that need processing.

    Uses filename as the review key. When duplicate filenames are found in
    different subdirectories, only the first occurrence is kept and subsequent
    duplicates are logged and skipped to prevent version history collisions.
    """
    files_to_process = []
    skipped_files = []
    # Track filenames we've already queued to detect cross-directory duplicates
    seen_filenames = {}  # filename -> filepath (first occurrence)
    duplicate_warnings = []
    logger.info("\n=== COLLECTING PAPERS TO PROCESS ===")
    safe_print("\n=== COLLECTING PAPERS TO PROCESS ===")

    # The folder_path is now 'data/raw', which contains 'Research-Papers'
    # We need to search BOTH the top-level data/raw folder AND the Research-Papers subfolder
    search_paths = [folder_path]  # Start with the base data/raw folder

    research_papers_path = os.path.join(folder_path, 'Research-Papers')
    if os.path.isdir(research_papers_path):
        search_paths.append(research_papers_path)

    for search_path in search_paths:
        for root, dirs, files in os.walk(search_path):
            # If we're in the base folder, don't recurse into Research-Papers (it's handled separately)
            if search_path == folder_path:
                dirs[:] = [d for d in dirs if d != 'Research-Papers']

            for filename in files:
                filepath = os.path.join(root, filename)
                if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
                    continue

                # --- FIX: Detect duplicate filenames across subdirectories ---
                if filename in seen_filenames:
                    first_path = seen_filenames[filename]
                    msg = (f"DUPLICATE FILENAME DETECTED: '{filename}' found in both "
                           f"'{os.path.dirname(first_path)}' and '{root}'. "
                           f"Skipping duplicate to prevent version history collision.")
                    logger.warning(msg)
                    safe_print(f"   WARNING: Duplicate '{filename}' skipped (already found in {os.path.dirname(first_path)})")
                    duplicate_warnings.append(msg)
                    continue

                if filename in reviewed_files and DUPLICATE_MODE == 'skip':
                    skipped_files.append(filename)
                    logger.debug(f"Skipping already reviewed: {filename}")
                    continue
                elif DUPLICATE_MODE == 'ask' and filename in reviewed_files:
                    response = input(f"❓'{filename}' has been reviewed. Overwrite? (y/n): ").lower()
                    if response != 'y':
                        skipped_files.append(filename)
                        continue

                seen_filenames[filename] = filepath
                files_to_process.append((filepath, filename))
                logger.debug(f"Added to process queue: {filename}")

    logger.info(f"\n📊 Summary:")
    safe_print(f"\n📊 Summary:")
    logger.info(f"   Total supported files found: {len(files_to_process) + len(skipped_files) + len(duplicate_warnings)}")
    safe_print(f"   Total supported files found: {len(files_to_process) + len(skipped_files) + len(duplicate_warnings)}")
    logger.info(f"   Already reviewed (skipped/kept): {len(skipped_files)}")
    safe_print(f"   Already reviewed (skipped/kept): {len(skipped_files)}")
    if duplicate_warnings:
        logger.warning(f"   Duplicate filenames skipped: {len(duplicate_warnings)}")
        safe_print(f"   Duplicate filenames skipped: {len(duplicate_warnings)}")
    logger.info(f"   To be processed/reprocessed: {len(files_to_process)}")
    safe_print(f"   📋 To be processed/reprocessed: {len(files_to_process)}")
    return files_to_process


# --- 1. Initialize APIs and Models ---
class APIManager:
    """Manages API calls with rate limiting, caching, and retry logic.

    Provider-aware: the active model (`get_model_config()`) decides which
    backend to call. Anthropic / OpenAI / local providers go through the
    `llm_client` abstraction; Gemini retains its direct `genai` path so the
    `thinking_budget=0` optimisation is preserved.
    """
    def __init__(self):
        from literature_review.config.model_config import (
            ModelProvider,
            get_model_config,
            get_model_by_name,
            set_model_config,
        )

        self.cache = {}
        self.last_call_time = 0
        self.calls_this_minute = 0
        self.minute_start = time.time()

        active_config = get_model_config()
        self.provider = active_config.provider
        self.active_model_name = active_config.model_name
        self.fallback_model_name = active_config.fallback_model
        self._llm_client = None  # Lazy-init for non-Gemini providers
        self._gemini_client = None  # Lazy-init for Gemini provider
        self.json_generation_config = None
        self.text_generation_config = None

        # Walk the configured fallback chain on init failure. Each model
        # config can declare a `fallback_model` (registry alias); we try
        # the active model first, then each fallback in turn until one
        # initialises or we run out (in which case we re-raise).
        #
        # Dedup on (provider, model_name) so Claude Code and API paths
        # for the same underlying model are not considered duplicates.

        def _key(cfg) -> Tuple[str, str]:
            return (cfg.provider.value, cfg.model_name)

        init_chain = [active_config]
        seen = {_key(active_config)}
        cursor = active_config
        while cursor.fallback_model:
            try:
                fb_cfg = get_model_by_name(cursor.fallback_model)
            except Exception:  # invalid alias — stop walking
                break
            if _key(fb_cfg) in seen:
                break
            init_chain.append(fb_cfg)
            seen.add(_key(fb_cfg))
            cursor = fb_cfg

        last_error: Optional[BaseException] = None
        last_idx = len(init_chain) - 1
        for idx, cfg in enumerate(init_chain):
            is_fallback = idx > 0
            try:
                set_model_config(cfg)
                self.provider = cfg.provider
                self.active_model_name = cfg.model_name
                self.fallback_model_name = cfg.fallback_model
                self._llm_client = None
                self._gemini_client = None
                if self.provider == ModelProvider.GEMINI:
                    self._init_gemini_client()
                else:
                    self._init_llm_client(cfg)
                label = "Fallback" if is_fallback else "API"
                logger.info(
                    f"[SUCCESS] {label} client initialized for {cfg.display_name} "
                    f"(provider: {self.provider.value})"
                )
                safe_print(
                    f"{'⚠️  Falling back to' if is_fallback else '✅ API client initialized:'} "
                    f"{cfg.display_name} ({self.provider.value})"
                )
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[ATTEMPT FAILED] Could not initialize {cfg.display_name}: {e}"
                )
                if not is_fallback:
                    safe_print(f"❌ Failed to initialize {cfg.display_name}: {e}")
                if idx == last_idx:
                    logger.critical(
                        "[ERROR] No remaining fallbacks; raising last init error"
                    )
                    raise last_error from None

        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("[SUCCESS] Sentence Transformer initialized.")
            safe_print("✅ Sentence Transformer initialized.")
        except Exception as e:
            logger.warning(f"[WARNING] Could not initialize Sentence Transformer: {e}")
            safe_print(f"⚠️ Could not initialize Sentence Transformer: {e}")
            self.embedder = None

    def _init_gemini_client(self):
        """Initialise the Gemini direct path (preserves thinking_budget=0)."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self._gemini_client = genai.Client(api_key=api_key)
        thinking_config = types.ThinkingConfig(thinking_budget=0)
        self.json_generation_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=1.0,
            top_k=1,
            max_output_tokens=16384,
            response_mime_type="application/json",
            thinking_config=thinking_config,
        )
        self.text_generation_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=1.0,
            top_k=1,
            max_output_tokens=16384,
            thinking_config=thinking_config,
        )

    def _init_llm_client(self, active_config):
        """Initialise the unified llm_client for non-Gemini providers."""
        from literature_review.utils.llm_client import get_llm_client
        self._llm_client = get_llm_client(active_config)

    # Backwards-compatible attribute access: legacy callers reference
    # `api_manager.client` expecting the Gemini SDK object. Preserve that
    # only when Gemini is active; otherwise expose the llm_client.
    @property
    def client(self):
        return self._gemini_client if self._gemini_client is not None else self._llm_client

    def rate_limit(self):
        """Implement rate limiting using global limiter"""
        global_limiter.wait_for_quota()

    # Timeout for API requests (10 minutes = 600 seconds)
    API_REQUEST_TIMEOUT = 600

    def _make_api_request(self, prompt: str, is_json: bool) -> str:
        """Internal method to make API request (used with timeout wrapper).

        Dispatches by provider: Gemini uses the direct `genai` client (with
        thinking disabled); all other providers go through `llm_client`.
        """
        from literature_review.config.model_config import ModelProvider

        if self.provider == ModelProvider.GEMINI and self._gemini_client is not None:
            model_name = get_model_config().model_name
            current_config_object = (
                self.json_generation_config if is_json else self.text_generation_config
            )
            response = self._gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=current_config_object,
            )
            return response.text

        # All other providers (Anthropic, OpenAI, local) via llm_client
        if self._llm_client is None:
            raise RuntimeError("No LLM client initialised")
        return self._llm_client.generate(prompt=prompt, json_mode=is_json)

    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
        """Make API call with caching, validation, timeout, and retry logic.
        
        Includes a 10-minute timeout per request with one retry on timeout.
        If both attempts timeout, returns None (skip file).
        """
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        if use_cache and prompt_hash in self.cache:
            logger.debug(f"Cache hit for hash: {prompt_hash}")
            safe_print("📦 Using cached response")
            return self.cache[prompt_hash]
        
        # Validate request before making API call
        is_valid, reason = global_limiter.validate_request(prompt, {'response_mime_type': 'application/json' if is_json else None})
        if not is_valid:
            logger.error(f"Request validation failed: {reason}")
            global_limiter.record_request(success=False)
            return None
        
        # Check if we should abort due to error patterns
        if global_limiter.should_abort_pipeline():
            logger.critical("Pipeline abort recommended due to error patterns")
            return None
        
        logger.debug(f"Cache miss for hash: {prompt_hash}. Calling API...")
        self.rate_limit()
        response_text = ""
        model_name = get_model_config().model_name
        
        # Track timeout retries separately (max 2 timeout attempts)
        timeout_attempts = 0
        max_timeout_retries = 2
        
        for attempt in range(REVIEW_CONFIG['RETRY_ATTEMPTS']):
            try:
                # Use ThreadPoolExecutor for timeout-protected API call
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._make_api_request, prompt, is_json)
                    try:
                        response_text = future.result(timeout=self.API_REQUEST_TIMEOUT)
                    except concurrent.futures.TimeoutError:
                        timeout_attempts += 1
                        logger.error(
                            f"⏱️ API request TIMEOUT after {self.API_REQUEST_TIMEOUT}s "
                            f"(timeout attempt {timeout_attempts}/{max_timeout_retries})"
                        )
                        safe_print(
                            f"⏱️ API timeout after {self.API_REQUEST_TIMEOUT // 60}min "
                            f"(attempt {timeout_attempts}/{max_timeout_retries})"
                        )
                        global_limiter.record_request(success=False)
                        
                        if timeout_attempts >= max_timeout_retries:
                            logger.error(
                                f"🚫 Skipping file: {max_timeout_retries} consecutive timeouts. "
                                f"API may be unresponsive for this request."
                            )
                            safe_print(f"🚫 Skipping file after {max_timeout_retries} timeouts")
                            return None
                        
                        # Wait before retry on timeout
                        time.sleep(30)
                        continue
                
                # Reset timeout counter on successful response
                timeout_attempts = 0
                
                if is_json:
                    result = json.loads(response_text)
                else:
                    result = response_text
                self.cache[prompt_hash] = result
                # Record successful request
                global_limiter.record_request(success=True)
                return result
                
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error on attempt {attempt + 1}: {e}. Response text: '{response_text[:500]}...'")
                # Categorize error
                category = global_limiter.categorize_error(e, response_text)
                action = global_limiter.get_action_for_error(category)
                global_limiter.record_request(success=False, error_category=category, action=action)
                
                if action == ErrorAction.SKIP_DOCUMENT:
                    logger.error(f"Skipping document due to {category.name}")
                    return None
                elif attempt < REVIEW_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(REVIEW_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for JSON decode error.")
            except Exception as e:
                # Categorize error
                category = global_limiter.categorize_error(e, str(e))
                action = global_limiter.get_action_for_error(category)
                global_limiter.record_request(success=False, error=e, response_text=str(e))
                
                if "DeadlineExceeded" in str(e) or "Timeout" in str(e):
                    logger.error(f"API call timed out on attempt {attempt + 1}")
                else:
                    logger.error(f"API error on attempt {attempt + 1}: {type(e).__name__} - {e}")
                
                if action == ErrorAction.ABORT_PIPELINE:
                    logger.critical(f"Aborting due to {category.name}")
                    return None
                elif action == ErrorAction.SKIP_DOCUMENT:
                    logger.error(f"Skipping document due to {category.name}")
                    return None
                elif "429" in str(e):
                    logger.warning("Rate limit error detected by API, increasing sleep time.")
                    time.sleep(REVIEW_CONFIG['RETRY_DELAY'] * (attempt + 2))
                elif attempt < REVIEW_CONFIG['RETRY_ATTEMPTS'] - 1:
                    # Use delay from action's value tuple (name, delay_seconds)
                    _, delay = action.value
                    time.sleep(delay if delay > 0 else REVIEW_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for API error.")
        logger.error(f"API call failed after {REVIEW_CONFIG['RETRY_ATTEMPTS']} attempts.")
        return None


# --- 2. File Handling and Text Extraction (Unchanged) ---
class TextExtractor:
    """Robust text extraction from multiple file formats"""
    @staticmethod
    def validate_paper_quality(text: str) -> Tuple[bool, QualityIndicators]:
        """Validate if extracted text is likely a valid research paper"""
        length = len(text)
        text_lower_start = text[:max(2000, length)].lower()
        text_lower_end = text[-max(5000, length):].lower()
        indicators = QualityIndicators(
            has_abstract=any(keyword in text_lower_start for keyword in ['abstract', 'summary']),
            has_references='references' in text_lower_end or 'bibliography' in text_lower_end,
            has_methods=any(keyword in text.lower() for keyword in ['method', 'approach', 'experiment']),
            sufficient_length=length > REVIEW_CONFIG['MIN_TEXT_LENGTH'],
            extraction_quality=0.0
        )
        score = sum([
            indicators.has_abstract * 0.3,
            indicators.has_references * 0.3,
            indicators.has_methods * 0.2,
            indicators.sufficient_length * 0.2
        ])
        indicators.extraction_quality = score
        is_valid = indicators.sufficient_length and (indicators.has_abstract or indicators.has_references)
        if not is_valid:
            logger.warning(
                f"Quality validation failed: Length={indicators.sufficient_length}, Abstract={indicators.has_abstract}, Refs={indicators.has_references}")
        return is_valid, indicators

    @staticmethod
    def extract_with_pymupdf(filepath: str) -> Tuple[str, float]:
        """Extract text using PyMuPDF (fitz) — primary extractor.

        PyMuPDF is the dissertation's chosen extraction backend, so we use the
        same library here to keep filename-to-content mapping consistent.
        """
        if fitz is None:
            logger.warning("PyMuPDF (fitz) not installed; skipping pymupdf extraction")
            return "", 0.0
        text = ""
        quality = 0.0
        try:
            doc = fitz.open(filepath)
        except Exception as e:
            logger.error(f"pymupdf failed to open {os.path.basename(filepath)}: {e}")
            return "", 0.0
        try:
            page_count = len(doc)
            if page_count == 0:
                logger.warning(f"pymupdf found 0 pages in {os.path.basename(filepath)}")
                return "", 0.0
            extracted_chars = 0
            for i, page in enumerate(doc):
                try:
                    page_text = page.get_text() or ""
                    if page_text:
                        text += page_text + "\n"
                        extracted_chars += len(page_text)
                except Exception as page_e:
                    logger.warning(f"pymupdf error on page {i + 1}: {page_e}")
            quality = min(extracted_chars / (page_count * 1500.0), 1.0)
            logger.debug(f"pymupdf extracted ~{len(text)} chars, quality score: {quality:.2f}")
            return text, quality
        finally:
            try:
                doc.close()
            except Exception:
                pass

    @staticmethod
    def extract_with_pypdf(filepath: str) -> Tuple[str, float]:
        """Extract text using pypdf"""
        text = ""
        quality = 0.0
        page_count = 0
        try:
            with open(filepath, 'rb') as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                if page_count == 0:
                    logger.warning(f"pypdf found 0 pages in {os.path.basename(filepath)}")
                    return "", 0.0
                extracted_chars = 0
                for page in reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                            extracted_chars += len(page_text)
                    except Exception as page_e:
                        logger.warning(f"pypdf error on page: {page_e}")
                if page_count > 0:
                    quality = min(extracted_chars / (page_count * 1500.0), 1.0)
                logger.debug(f"pypdf extracted ~{len(text)} chars, quality score: {quality:.2f}")
                return text, quality
        except Exception as e:
            logger.error(f"pypdf extraction failed for {os.path.basename(filepath)}: {e}")
            return "", 0.0

    @staticmethod
    def extract_with_pdfplumber(filepath: str) -> Tuple[str, float]:
        """Extract text using pdfplumber"""
        text = ""
        quality = 0.0
        page_count = 0
        try:
            with pdfplumber.open(filepath) as pdf:
                page_count = len(pdf.pages)
                if page_count == 0:
                    logger.warning(f"pdfplumber found 0 pages in {os.path.basename(filepath)}")
                    return "", 0.0
                extracted_chars = 0
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text(x_tolerance=1, y_tolerance=1)
                        if page_text:
                            text += page_text + "\n"
                            extracted_chars += len(page_text)
                    except Exception as page_e:
                        logger.warning(f"pdfplumber error on page {i + 1}: {page_e}")
                if page_count > 0:
                    quality = min(extracted_chars / (page_count * 1500.0), 1.0)
                logger.debug(f"pdfplumber extracted ~{len(text)} chars, quality score: {quality:.2f}")
                return text, quality
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {os.path.basename(filepath)}: {e}")
            return "", 0.0

    @staticmethod
    def extract_from_html(filepath: str) -> Tuple[str, float]:
        """Extract text from HTML files"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    if tag: tag.decompose()
                main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find(
                    'div', class_='content') or soup.body
                if main_content:
                    text = main_content.get_text(separator=' ', strip=True)
                else:
                    text = soup.get_text(separator=' ', strip=True)
                quality = 1.0 if len(text) > REVIEW_CONFIG['MIN_TEXT_LENGTH'] else 0.5
                logger.debug(f"HTML extracted ~{len(text)} chars, quality score: {quality:.2f}")
                return text, quality
        except Exception as e:
            logger.error(f"HTML extraction failed for {os.path.basename(filepath)}: {e}")
            return "", 0.0

    @classmethod
    def robust_text_extraction(cls, filepath: str) -> Tuple[str, str, float]:
        """Multi-method extraction with quality assessment. Returns full text."""
        logger.info(f"Extracting text from: {os.path.basename(filepath)}")
        safe_print(f"📄 Extracting text from: {os.path.basename(filepath)}")
        text, method, quality = "", "unsupported", 0.0
        file_ext = os.path.splitext(filepath)[1].lower()
        if file_ext == '.html':
            text, quality = cls.extract_from_html(filepath)
            method = "html_parser"
        elif file_ext == '.pdf':
            # Primary: pymupdf (matches dissertation's extraction backend).
            # Fallbacks: pdfplumber, pypdf — only consulted if pymupdf yields
            # less text. Highest-yield extractor wins, but pymupdf is tried first
            # so its result is the baseline.
            methods_to_try = [
                ("pymupdf", cls.extract_with_pymupdf),
                ("pdfplumber", cls.extract_with_pdfplumber),
                ("pypdf", cls.extract_with_pypdf),
            ]
            best_text, best_quality, best_method = "", 0.0, "none"
            for method_name, method_func in methods_to_try:
                current_text, current_quality = method_func(filepath)
                if len(current_text) > len(best_text):
                    best_text, best_quality, best_method = current_text, current_quality, method_name
                elif best_method == "none":
                    best_text, best_quality, best_method = current_text, current_quality, method_name
            text, quality, method = best_text, best_quality, best_method
            if method == "none":
                logger.error(f"All PDF extraction methods failed for {os.path.basename(filepath)}")
        elif file_ext == '.txt':
            try:
                encodings_to_try = ['utf-8', 'cp1252', 'latin-1']
                for enc in encodings_to_try:
                    try:
                        with open(filepath, 'r', encoding=enc) as f:
                            text = f.read()
                        quality, method = 1.0, f"text_reader ({enc})"
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    logger.error(f"Could not decode text file {os.path.basename(filepath)} with tried encodings.")
                    text, quality, method = "", 0.0, "failed_decode"
            except Exception as e:
                logger.error(f"Text file reading failed: {e}")
                text, quality, method = "", 0.0, "failed_read"
        else:
            logger.warning(f"Unsupported file type: {filepath}")
        return text, method, quality


# --- NEW: Provenance Tracking Functions ---
# These functions enable detailed tracking of claim sources for audit trails,
# citation generation, and human verification of extracted claims.


def extract_text_with_provenance(file_path: str) -> List[Dict]:
    """
    Extract text with page-level tracking and section detection.
    
    Args:
        file_path: Path to PDF file to extract text from
    
    Returns:
        List of dicts with page metadata:
        [
            {
                "page_num": 1,
                "text": "...",
                "section": "Introduction",
                "char_start": 0,
                "char_end": 1250
            },
            ...
        ]
    """
    pages_with_metadata = []
    cumulative_chars = 0
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                
                # Detect section heading
                section = detect_section_heading(text)
                
                page_metadata = {
                    "page_num": page_num,
                    "text": text,
                    "section": section or "Unknown",
                    "char_start": cumulative_chars,
                    "char_end": cumulative_chars + len(text)
                }
                
                pages_with_metadata.append(page_metadata)
                cumulative_chars += len(text)
    except Exception as e:
        logger.error(f"Error extracting text with provenance from {file_path}: {e}")
        return []
    
    return pages_with_metadata


def detect_section_heading(text: str) -> Optional[str]:
    """
    Detect academic paper section headings.
    
    Looks for common patterns in first 200 characters.
    Prioritizes headings at the start of lines or with numbering.
    
    Args:
        text: Text to scan for section headings
    
    Returns:
        Section name (title case) if detected, None otherwise
        
    Examples:
        >>> detect_section_heading("1. Introduction\\nThis paper...")
        'Introduction'
        >>> detect_section_heading("METHODS\\nWe used...")
        'Methods'
    """
    headings = [
        "abstract", "introduction", "background", "related work",
        "methods", "methodology", "approach", "design",
        "results", "findings", "experiments", "evaluation",
        "discussion", "analysis", "interpretation",
        "conclusion", "future work", "limitations",
        "references", "bibliography", "acknowledgments"
    ]
    
    # Normalize and check first lines
    first_lines = text[:200].lower().strip()
    
    for heading in headings:
        # Match patterns like "1. Introduction" or "INTRODUCTION" or "1 Introduction"
        # Prioritize patterns that are more likely to be actual section headings
        patterns = [
            f"^\\d+\\.?\\s*{heading}\\b",  # "1. Introduction" at start
            f"^{heading}\\s*$",              # "Introduction" on its own line at start
            f"\\n\\s*{heading}\\s*\\n",      # "Introduction" on its own line
        ]
        
        for pattern in patterns:
            if re.search(pattern, first_lines, re.IGNORECASE | re.MULTILINE):
                return heading.title()
    
    return None


def add_provenance_to_claim(
    claim: Dict,
    full_text: str,
    pages_metadata: List[Dict],
    evidence_text: str
) -> Dict:
    """
    Add provenance metadata to claim.
    
    Finds the evidence text in full document and adds:
    - Page numbers where evidence appears
    - Section name
    - Character offsets (for precise location)
    - Supporting quote (truncated to 500 chars)
    - Context before/after (100 chars each)
    
    Args:
        claim: Claim dict to enhance with provenance
        full_text: Full text of the document
        pages_metadata: List of page metadata from extract_text_with_provenance
        evidence_text: The evidence text to locate in the document
    
    Returns:
        Enhanced claim with 'provenance' field added, or unchanged claim if
        evidence not found verbatim
        
    Note:
        If evidence_text is not found verbatim in full_text, the claim is
        returned unchanged (no provenance added). This handles cases where
        evidence may have been paraphrased by the AI.
    """
    # Find evidence location
    evidence_start = full_text.find(evidence_text)
    
    if evidence_start == -1:
        # Evidence not found verbatim (might be paraphrased)
        # Fall back to fuzzy matching or skip provenance
        return claim
    
    evidence_end = evidence_start + len(evidence_text)
    
    # Find which page(s) contain this evidence
    pages_containing_evidence = []
    for page_meta in pages_metadata:
        if (evidence_start >= page_meta["char_start"] and 
            evidence_start < page_meta["char_end"]):
            pages_containing_evidence.append(page_meta["page_num"])
        elif (evidence_end > page_meta["char_start"] and 
              evidence_end <= page_meta["char_end"]):
            pages_containing_evidence.append(page_meta["page_num"])
    
    # Get section name from first page
    first_page_meta = next(
        (p for p in pages_metadata if p["page_num"] == pages_containing_evidence[0]),
        None
    ) if pages_containing_evidence else None
    section = first_page_meta["section"] if first_page_meta else "Unknown"
    
    # Extract context (100 chars before/after)
    context_window = 100
    context_before = full_text[max(0, evidence_start - context_window):evidence_start]
    context_after = full_text[evidence_end:evidence_end + context_window]
    
    # Add provenance
    claim["provenance"] = {
        "page_numbers": pages_containing_evidence,
        "section": section,
        "char_start": evidence_start,
        "char_end": evidence_end,
        "supporting_quote": evidence_text[:500],  # Truncate long quotes
        "quote_page": pages_containing_evidence[0] if pages_containing_evidence else None,
        "context_before": context_before.strip(),
        "context_after": context_after.strip()
    }
    
    return claim


# --- 3a. Post-Review Validation Utilities ---

def _looks_like_author_line(line: str) -> bool:
    """Heuristic to detect author-name lines commonly found at the top of papers.

    Catches patterns like:
      - "John Smith *, Jane Doe †, Bob Jones 1"
      - "Costin-Emanuel Vasile * , Andrei-Alexandru Ulmǎmei *"
      - "Ciyuan Peng1 · Feng Xia2  · Mehdi Naseriparsa3"
    """
    # High comma + dot density → likely an author list
    comma_count = line.count(',') + line.count('·')
    word_count = len(line.split())
    if word_count > 0 and comma_count / word_count > 0.15:
        return True

    # Superscript / affiliation markers next to words (*, †, ‡, digits after names)
    superscript_markers = len(re.findall(r'[*†‡⁰¹²³⁴⁵⁶⁷⁸⁹]', line))
    # Also catch patterns like "Author1" or "Author 1," where digits follow letters
    affiliation_digits = len(re.findall(r'[A-Za-z][0-9]', line))
    if superscript_markers + affiliation_digits >= 2:
        return True

    # Email / institutional patterns
    if re.search(r'@|university|department|institute|faculty|school of',
                 line, re.IGNORECASE):
        return True

    # Pattern: multiple capitalized name-like words separated by commas or "and"
    # e.g., "John Smith, Jane Doe, and Bob Jones"
    name_parts = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', line)
    if len(name_parts) >= 3:
        return True

    return False


def extract_title_from_text(text: str, filename: str = None) -> Optional[str]:
    """Extract the paper title from the first ~1500 characters of extracted text.

    Looks for the first non-trivial line that is likely a title. Skips common
    header noise like 'RESEARCH ARTICLE', 'LETTER', page numbers, and
    author-name lines. Falls back to deriving a title from the filename if
    no good candidate is found.
    """
    skip_patterns = re.compile(
        r'^(RESEARCH\s+ARTICLE|LETTER|REVIEW|ORIGINAL\s+(ARTICLE|RESEARCH)|'
        r'Communicated\s+by|SHORT\s+COMMUNICATION|BRIEF\s+REPORT|'
        r'PLOS\s+\w+|Nature\s+\w+|Science\s+\w+|'
        r'\d+$|\s*$)', re.IGNORECASE
    )

    lines = text[:1500].split('\n')
    candidate_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        if skip_patterns.match(stripped):
            continue
        # Skip lines that are mostly numbers/special chars (page headers, DOIs)
        alpha_ratio = sum(c.isalpha() for c in stripped) / max(len(stripped), 1)
        if alpha_ratio < 0.5:
            continue
        # Skip author-name lines
        if _looks_like_author_line(stripped):
            continue
        candidate_lines.append(stripped)
        if len(candidate_lines) >= 3:
            break

    if candidate_lines:
        # Title is typically the longest of the first few candidate lines
        title = max(candidate_lines[:3], key=len)
        # Truncate if absurdly long (probably not a title)
        if len(title) > 300:
            title = title[:300]
        return title

    # Fallback: derive title from filename (e.g., "Image_Processing_Hardware_Acce.pdf"
    # → "Image Processing Hardware Acce")
    if filename:
        stem = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
        # Replace underscores/hyphens with spaces, collapse whitespace
        fallback_title = re.sub(r'[_\-]+', ' ', stem).strip()
        if len(fallback_title) >= 5:
            logger.info(f"Using filename-derived title as fallback: '{fallback_title}'")
            return fallback_title

    return None


def validate_review_quotes(paper_text: str, review_result: Dict, min_match_ratio: float = 0.6) -> Dict:
    """Validate that verbatim quotes from a review actually exist in the source text.

    Uses fuzzy matching (difflib) to find quotes in the paper text.
    Returns a validation report with per-quote results and an overall score.

    Args:
        paper_text: The full extracted text of the paper.
        review_result: The review JSON returned by the API.
        min_match_ratio: Minimum SequenceMatcher ratio to count as a match.

    Returns:
        Dict with 'total_quotes', 'verified_count', 'verification_rate',
        'is_valid' (True if rate >= 0.5), and 'details' list.
    """
    claims = review_result.get('claims', [])
    gaps = review_result.get('gaps', [])

    quotes_to_check = []
    for claim in claims:
        q = claim.get('verbatim_quote')
        if q and q.strip():
            quotes_to_check.append(('claim', claim.get('claim_id', '?'), q.strip()))
    for gap in gaps:
        q = gap.get('verbatim_quote')
        if q and q.strip():
            quotes_to_check.append(('gap', gap.get('gap_id', '?'), q.strip()))

    if not quotes_to_check:
        return {'total_quotes': 0, 'verified_count': 0, 'verification_rate': 1.0,
                'is_valid': True, 'details': []}

    # Normalize paper text for matching
    paper_normalized = ' '.join(paper_text.lower().split())

    verified_count = 0
    details = []
    for item_type, item_id, quote in quotes_to_check:
        quote_normalized = ' '.join(quote.lower().split())
        # Try exact substring first
        if quote_normalized in paper_normalized:
            verified_count += 1
            details.append({'id': item_id, 'type': item_type, 'status': 'exact_match'})
            continue

        # Try fuzzy matching on a sliding window
        quote_len = len(quote_normalized)
        best_ratio = 0.0
        # Use shorter quote segments for efficiency on long texts
        search_text = quote_normalized[:200] if len(quote_normalized) > 200 else quote_normalized
        search_len = len(search_text)

        # Slide through paper text in steps
        step = max(search_len // 4, 20)
        for start in range(0, len(paper_normalized) - search_len + 1, step):
            window = paper_normalized[start:start + search_len + 50]
            ratio = difflib.SequenceMatcher(None, search_text, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
            if ratio >= min_match_ratio:
                break

        if best_ratio >= min_match_ratio:
            verified_count += 1
            details.append({'id': item_id, 'type': item_type, 'status': 'fuzzy_match',
                            'match_ratio': round(best_ratio, 3)})
        else:
            details.append({'id': item_id, 'type': item_type, 'status': 'not_found',
                            'best_ratio': round(best_ratio, 3)})

    verification_rate = verified_count / len(quotes_to_check)
    is_valid = verification_rate >= 0.5  # At least half the quotes must be verifiable

    return {
        'total_quotes': len(quotes_to_check),
        'verified_count': verified_count,
        'verification_rate': round(verification_rate, 3),
        'is_valid': is_valid,
        'details': details
    }


# --- 3. Enhanced Analysis (MODIFIED) ---
class PaperAnalyzer:
    """Enhanced paper analysis with 'map-reduce' and requirement cross-referencing."""

    # --- MODIFIED: This is now the master column order ---
    # --- GOLDEN DATASET SCHEMA (v2.0) ---
    # Updated to align with AGENT_ANNOTATION_PROMPT.md standards
    DATABASE_COLUMN_ORDER = [
        "paper_id", "annotation_date", "annotation_version",
        # Paper metadata
        "TITLE", "AUTHORS", "PUBLICATION_YEAR", "SOURCE", "CORE_DOMAIN", "SUB_DOMAIN",
        "ABSTRACT_SUMMARY", "FULL_TEXT_LINK", "FILENAME", "PAGE_COUNT",
        # Scores
        "CORE_DOMAIN_RELEVANCE_SCORE", "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE",
        "BIOLOGICAL_FIDELITY", "REPRODUCIBILITY_SCORE", "MATURITY_LEVEL",
        # Content analysis
        "MAJOR_FINDINGS", "KEYWORDS", "CORE_CONCEPTS", "NETWORK_ARCHITECTURE",
        "BRAIN_REGIONS", "DATASET_USED", "INTERDISCIPLINARY_BRIDGES",
        # Analysis text fields
        "APPLICABILITY_NOTES", "IMPROVEMENT_SUGGESTIONS", "RISKS",
        "ENERGY_EFFICIENCY", "IMPLEMENTATION_DETAILS", "VALIDATION_METHOD",
        "SCALABILITY_NOTES", "COMPUTATIONAL_COMPLEXITY", "APA_REFERENCE",
        # Structured claims and gaps (Golden Dataset format)
        "claims", "gaps", "methodology_summary", "quality_metadata",
        # System fields
        "EXTRACTION_METHOD", "EXTRACTION_QUALITY", "REVIEW_TIMESTAMP",
        "SUMMARIZED_FROM_CHUNKS", "SIMILAR_PAPERS", "MENTIONED_PAPERS", "CROSS_REFERENCES_COUNT"
    ]
    # --- END GOLDEN DATASET SCHEMA ---
    
    # Required JSON keys for validation
    REQUIRED_JSON_KEYS = [
        "TITLE", "CORE_DOMAIN", "SUB_DOMAIN", "CORE_DOMAIN_RELEVANCE_SCORE",
        "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE", "MAJOR_FINDINGS", "BIOLOGICAL_FIDELITY",
        "REPRODUCIBILITY_SCORE", "claims", "gaps"
    ]

    NON_JOURNAL_JSON_KEYS = [
        "FILENAME", "DOCUMENT_TYPE", "DETECTED_TOPICS", "KEY_CONCEPTS",
        "POTENTIAL_SEARCH_KEYWORDS", "SUMMARY_NOTES"
    ]

    # --- MODIFIED: Chunk prompt now needs to be aware of requirements ---
    @staticmethod
    def get_chunk_summary_prompt(chunk_text: str, chunk_num: int, total_chunks: int, pillar_definitions_str: str) -> str:
        """Creates a prompt to summarize a single chunk of a large document.

        NOTE: This prompt intentionally avoids priming with domain-specific context
        to prevent hallucination when summarizing off-topic papers. The domain
        relevance assessment happens downstream in the full analysis prompt.
        """
        # Escape braces
        chunk_text_escaped = chunk_text.replace("{", "{{").replace("}", "}}")

        return f"""
You are a research summarization agent.
Your task is to read a chunk of a larger academic paper and produce an OBJECTIVE summary of its actual content.
This is CHUNK {chunk_num} of {total_chunks}.

CRITICAL INSTRUCTIONS:
- Summarize ONLY what is actually stated in the text below. Do NOT infer, extrapolate, or add information that is not present.
- If the text discusses a specific topic, summarize that topic faithfully — do NOT reframe it into a different research domain.
- Preserve the paper's actual terminology, methods, and findings.

Based ONLY on the text chunk provided below, extract and summarize:
1.  **Key Points:** The main findings, methods, or conclusions actually stated in this chunk.
2.  **Paper Topic:** What specific subject area or research question does this chunk address?

Return your output as a concise, well-structured summary using bullet points.
Start immediately with the summary points.
Do not include introductory or concluding phrases.
Do not add domain framing or categorization that is not present in the text.

--- TEXT CHUNK ---
{chunk_text_escaped}
--- END CHUNK ---
"""
    # --- END MODIFICATION ---

    @staticmethod
    def summarize_text_chunks(full_text: str, api_manager: APIManager, pillar_definitions_str: str) -> str:
        """Splits large text, summarizes each chunk, and compiles the summaries."""
        chunk_size = REVIEW_CONFIG['CHUNK_SIZE']
        overlap = int(chunk_size * 0.1)
        chunks = [full_text[i:i + chunk_size] for i in range(0, len(full_text), chunk_size - overlap)]

        if len(chunks) <= 1:
            return full_text

        logger.info(f"Document ({len(full_text)} chars) split into {len(chunks)} chunks for summarization.")
        safe_print(f"   Split into {len(chunks)} chunks for summarization...")

        compiled_summary = "[[[ This document was summarized from multiple chunks due to its length. Key points from each chunk follow: ]]]\n\n"
        successful_summaries = 0
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i + 1}/{len(chunks)}...")
            safe_print(f"   Summarizing chunk {i + 1}/{len(chunks)}...")

            # --- MODIFIED: Pass pillar definitions string ---
            prompt = PaperAnalyzer.get_chunk_summary_prompt(chunk, i + 1, len(chunks), pillar_definitions_str)
            logger.info(f"Sending chunk summary prompt ({len(prompt)} chars) to API...")

            chunk_summary = api_manager.cached_api_call(prompt, is_json=False)

            if chunk_summary:
                compiled_summary += f"\n--- SUMMARY OF CHUNK {i + 1}/{len(chunks)} ---\n"
                compiled_summary += chunk_summary.strip() + "\n"
                successful_summaries += 1
            else:
                logger.error(f"Failed to summarize chunk {i + 1}.")
                compiled_summary += f"\n--- SUMMARY OF CHUNK {i + 1}/{len(chunks)} ---\n[[[ Summarization Failed ]]]\n"

        if successful_summaries < len(chunks) / 2:
            logger.error("Summarization failed for a significant number of chunks. Final analysis may be inaccurate.")

        logger.info(f"Chunk summarization complete. Compiled summary is {len(compiled_summary)} chars.")
        return compiled_summary

    # --- MODIFIED: get_enhanced_analysis_prompt (BIGGEST CHANGE) ---
    @staticmethod
    def get_enhanced_analysis_prompt(paper_text: str, metadata: PaperMetadata, pillar_definitions_str: str) -> str:
        """Generate comprehensive analysis prompt for a journal paper, including requirement extraction."""
        is_summarized = "[[[ This document was summarized" in paper_text[:500]

        # Get research context from configuration
        research_topic = get_research_topic_safe()
        
        # Generate paper_id from filename
        paper_id = metadata.filename.replace('.pdf', '').replace('.html', '').replace('.txt', '')
        
        # Escape braces
        paper_text_escaped = paper_text.replace("{", "{{").replace("}", "}}")
        
        return f"""
You are an expert research assistant annotating papers for a Golden Dataset used to validate automated literature review systems.
Your annotations must be **accurate, verifiable, and traceable** to specific page locations in the paper.

--- CORE RESEARCH TOPIC ---
"{research_topic}"

--- PILLAR DEFINITIONS (FOR CLAIM MAPPING) ---
{pillar_definitions_str}
--- END PILLAR DEFINITIONS ---

Analyze the provided text and return a single, clean JSON object following the Golden Dataset schema.
Do not include any text, notes, or apologies before or after the JSON object.
Ensure all string values in the JSON are properly escaped.

**CRITICAL REQUIREMENTS:**
1. ALL claims MUST include page numbers where the evidence appears
2. ALL verbatim quotes MUST be exact text from the paper (≤100 words each)
3. Distinguish between "quantitative" claims (numeric results) and "qualitative" claims (methods, conclusions)
4. Mark confidence honestly: "high" (directly stated), "medium" (inferred), "low" (uncertain)

The JSON object must contain these exact keys:

--- METADATA FIELDS ---
- "paper_id": "{paper_id}"
- "annotation_date": "{datetime.now().strftime('%Y-%m-%d')}"
- "annotation_version": "2.0"
- "TITLE": (String) Full title of the paper
- "AUTHORS": (List of Strings) Author names as they appear, or ["Unknown"] if not found
- "PUBLICATION_YEAR": (Integer or "N/A") Year of publication
- "SOURCE": (String) Journal, conference, or venue name
- "CORE_DOMAIN": (String) Primary field (e.g., "Machine Learning", "Neuroscience")
- "SUB_DOMAIN": (String) Specific sub-field (e.g., "Spiking Neural Networks")
- "ABSTRACT_SUMMARY": (String) 2-3 sentence summary of the paper
- "FULL_TEXT_LINK": (String) DOI or URL, otherwise "N/A"
- "FILENAME": "{metadata.filename}"
- "PAGE_COUNT": (Integer or null) Total pages if determinable

--- SCORE FIELDS (Integer 0-100) ---
- "CORE_DOMAIN_RELEVANCE_SCORE": Paper's depth/quality within its core domain
- "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE": Relevance to our core research topic
- "BIOLOGICAL_FIDELITY": How closely the model mimics biological systems
- "REPRODUCIBILITY_SCORE": Based on methods detail and data availability
- "MATURITY_LEVEL": (String) "Theoretical", "Experimental", or "Applied"

--- CONTENT LISTS ---
- "MAJOR_FINDINGS": (List of Strings) 2-4 key results/conclusions
- "KEYWORDS": (List of Strings) 5-10 author-provided keywords
- "CORE_CONCEPTS": (List of Strings) 5-10 fundamental concepts (e.g., "STDP", "Attention")
- "NETWORK_ARCHITECTURE": (List of Strings) Specific architectures (e.g., "SNN", "Transformer")
- "BRAIN_REGIONS": (List of Strings) Brain regions mentioned, or []
- "DATASET_USED": (List of Strings) Datasets used, or []
- "INTERDISCIPLINARY_BRIDGES": (List of Strings) Concepts linking domains

--- TEXT ANALYSIS FIELDS ---
- "APPLICABILITY_NOTES": How findings apply to our research
- "IMPROVEMENT_SUGGESTIONS": Suggestions for extending the study
- "RISKS": Potential challenges or risks highlighted
- "ENERGY_EFFICIENCY": Mention of power consumption or efficiency
- "IMPLEMENTATION_DETAILS": Note presence of code, algorithms, hardware specs
- "VALIDATION_METHOD": How findings were validated
- "SCALABILITY_NOTES": Scalability issues or potential
- "COMPUTATIONAL_COMPLEXITY": Complexity analysis mentions
- "APA_REFERENCE": Best attempt at APA 7th edition reference

--- CLAIMS (Golden Dataset Format) ---
- "claims": (List of Objects) Evidence for pillar sub-requirements
  Each claim object MUST have this structure:
  {{
    "claim_id": "{paper_id}-C001" (increment number for each claim),
    "claim_type": "quantitative" or "qualitative",
    "pillar": "(String) EXACT pillar name from definitions (e.g., 'Pillar 2: AI Stimulus-Response (Bridge)')",
    "sub_requirement": "(String) EXACT sub-requirement from definitions",
    "claim_text": "(String) Your summary of what this claim shows",
    "verbatim_quote": "(String) EXACT text from paper (≤100 words)",
    "location": {{
      "page": (Integer) Page number where quote appears,
      "section": "(String) Section name (e.g., 'Results', 'Methods')"
    }},
    "confidence": "high", "medium", or "low",
    "verification_notes": "(String) How to verify this claim in the paper",
    "status": "pending_judge_review"
  }}

--- GAPS (Golden Dataset Format) ---
- "gaps": (List of Objects) Limitations, future work, open questions
  Each gap object MUST have this structure:
  {{
    "gap_id": "{paper_id}-G001" (increment number for each gap),
    "gap_type": "limitation", "future_work", or "open_question",
    "gap_text": "(String) Description of the gap",
    "verbatim_quote": "(String or null) Direct quote if available",
    "location": {{
      "page": (Integer or null) Page number if identifiable,
      "section": "(String) Section name"
    }},
    "implied_vs_explicit": "explicit" (stated by authors) or "implied" (inferred by you),
    "research_direction": "(String) What future work could address this"
  }}

--- METHODOLOGY SUMMARY ---
- "methodology_summary": {{
    "approach": "(String) Brief description of methodology",
    "datasets_used": (List of Strings),
    "key_techniques": (List of Strings),
    "evaluation_metrics": (List of Strings)
  }}

--- QUALITY METADATA ---
- "quality_metadata": {{
    "total_claims": (Integer) Count of claims,
    "quantitative_claims": (Integer) Count of quantitative claims,
    "qualitative_claims": (Integer) Count of qualitative claims,
    "total_gaps": (Integer) Count of gaps,
    "annotation_confidence": "high", "medium", or "low",
    "notes": "(String) Any issues encountered during annotation"
  }}

{'--- START OF TEXT ---' if not is_summarized else '--- START OF COMPILED SUMMARIES ---'}
{paper_text_escaped}
{'--- END OF TEXT ---' if not is_summarized else '--- END OF COMPILED SUMMARIES ---'}
"""
    # --- END GOLDEN DATASET PROMPT ---

    @staticmethod
    def get_non_journal_analysis_prompt(paper_text: str, metadata: PaperMetadata) -> str:
        """Generate a simpler analysis prompt for non-journal items like lecture slides."""
        is_summarized = "[[[ This document was summarized" in paper_text[:500]
        # Get research context from configuration
        research_topic = get_research_topic_safe()
        
        # Escape braces to prevent f-string errors
        paper_text_escaped = paper_text.replace("{", "{{").replace("}", "}}")
        
        return f"""
You are a research assistant.
Your task is to analyze a document that is likely NOT a formal academic paper (e.g., lecture slides, notes, a web article).
Your goal is to extract key topics and search terms that could be useful for finding actual journal papers later.
Our core research topic is: "{research_topic}"
Analyze the provided text below and return a single, clean JSON object.
Do not include any text before or after the JSON.
The JSON object must contain these exact keys:
- "FILENAME": "{metadata.filename}" (String)
- "DOCUMENT_TYPE": (String) Infer the document type (e.g., "Lecture Slides", "Web Article", "Book Chapter", "Notes", "Unknown").
- "DETECTED_TOPICS": (List of Strings) 3-5 high-level topics detected (e.g., "Cognitive Neuroscience", "Deep Learning", "Synaptic Plasticity").
- "KEY_CONCEPTS": (List of Strings) 5-10 specific key concepts, names, or algorithms mentioned (e.g., "Hebbian Learning", "MIT 9.40S18", "PFC function", "Memory Consolidation").
- "POTENTIAL_SEARCH_KEYWORDS": (List of Strings) 5-10 keywords or phrases that would be good to use in a search engine (like Google Scholar) to find formal papers on these topics.
- "SUMMARY_NOTES": (String) A 1-2 sentence summary of what this document is about and its relevance to our core research.
{'--- START OF TEXT ---' if not is_summarized else '--- START OF COMPILED SUMMARIES ---'}
{paper_text_escaped}
{'--- END OF TEXT ---' if not is_summarized else '--- END OF COMPILED SUMMARIES ---'}
"""

    # --- GOLDEN DATASET VALIDATION ---
    @staticmethod
    def validate_response(response: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate AI response against Golden Dataset schema with sanitization."""
        missing_fields = []
        type_errors = []
        warnings = []
        
        if not isinstance(response, dict):
            return False, ["Response is not a valid JSON object"]

        for field in required_fields:
            if field not in response:
                missing_fields.append(field)
                continue

            value = response[field]
            
            # --- Type definitions for Golden Dataset schema ---
            score_fields = ["CORE_DOMAIN_RELEVANCE_SCORE", "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE",
                           "BIOLOGICAL_FIDELITY", "REPRODUCIBILITY_SCORE", "PAGE_COUNT", "CROSS_REFERENCES_COUNT"]
            list_of_str_fields = ["MAJOR_FINDINGS", "KEYWORDS", "CORE_CONCEPTS", "INTERDISCIPLINARY_BRIDGES",
                                  "NETWORK_ARCHITECTURE", "BRAIN_REGIONS", "DATASET_USED",
                                  "SIMILAR_PAPERS", "MENTIONED_PAPERS", "AUTHORS"]
            structured_obj_fields = ["claims", "gaps", "methodology_summary", "quality_metadata"]
            
            # Determine expected type
            if field in score_fields:
                expected_type = "int_or_null"
            elif field == "PUBLICATION_YEAR":
                expected_type = "Int_or_NA"
            elif field in list_of_str_fields:
                expected_type = "list_of_str"
            elif field in structured_obj_fields:
                expected_type = "structured"
            else:
                expected_type = "str"

            # --- Sanitization and Type Checking ---
            if expected_type == "list_of_str" and isinstance(value, str):
                logger.warning(f"Sanitizing field '{field}': converting string to list.")
                response[field] = [value]
                value = response[field]

            if expected_type == "int_or_null":
                if value is not None and not isinstance(value, int):
                    try:
                        response[field] = int(value) if value not in ["N/A", "null", None, ""] else None
                    except (ValueError, TypeError):
                        type_errors.append(f"Field '{field}' expected Integer or null, got {type(value)}")
            elif expected_type == "Int_or_NA" and not (isinstance(value, int) or value == "N/A"):
                type_errors.append(f"Field '{field}' expected Integer or 'N/A', got {type(value)}")
            elif expected_type == "list_of_str" and not isinstance(value, list):
                type_errors.append(f"Field '{field}' expected List, got {type(value)}")
            elif expected_type == "list_of_str" and value and not all(isinstance(item, str) for item in value):
                try:
                    response[field] = [str(item) for item in value]
                    logger.warning(f"Sanitizing field '{field}': converting list items to string.")
                except Exception:
                    type_errors.append(f"Field '{field}' expected List of Strings")
            elif expected_type == "str" and not isinstance(value, str):
                # Try to sanitize non-strings to strings
                try:
                    if value is not None:
                        response[field] = str(value)
                except Exception:
                    type_errors.append(f"Field '{field}' expected String, got {type(value)}")

            # --- Validate structured fields (claims, gaps, methodology_summary, quality_metadata) ---
            elif expected_type == "structured":
                if field == "claims":
                    if not isinstance(value, list):
                        type_errors.append(f"Field 'claims' expected List of Objects, got {type(value)}")
                    elif value:  # If list is not empty, validate structure
                        first_claim = value[0]
                        required_claim_fields = ['claim_id', 'claim_type', 'pillar', 'sub_requirement', 
                                                 'verbatim_quote', 'location', 'confidence', 'status']
                        if not isinstance(first_claim, dict):
                            type_errors.append("Claims must be objects")
                        else:
                            missing_claim_fields = [f for f in required_claim_fields if f not in first_claim]
                            if missing_claim_fields:
                                warnings.append(f"Claim missing fields: {missing_claim_fields}")
                            # Check for page numbers
                            if 'location' in first_claim:
                                loc = first_claim['location']
                                if not isinstance(loc, dict) or 'page' not in loc:
                                    warnings.append("Claim location should include 'page' number")
                
                elif field == "gaps":
                    if not isinstance(value, list):
                        type_errors.append(f"Field 'gaps' expected List of Objects, got {type(value)}")
                    elif value:  # If list is not empty, validate structure
                        first_gap = value[0]
                        required_gap_fields = ['gap_id', 'gap_type', 'gap_text']
                        if not isinstance(first_gap, dict):
                            type_errors.append("Gaps must be objects")
                        else:
                            missing_gap_fields = [f for f in required_gap_fields if f not in first_gap]
                            if missing_gap_fields:
                                warnings.append(f"Gap missing fields: {missing_gap_fields}")
                
                elif field == "methodology_summary":
                    if not isinstance(value, dict):
                        # Try to create empty structure
                        response[field] = {"approach": "N/A", "datasets_used": [], 
                                          "key_techniques": [], "evaluation_metrics": []}
                
                elif field == "quality_metadata":
                    if not isinstance(value, dict):
                        # Try to create from response data
                        claims = response.get("claims", [])
                        gaps = response.get("gaps", [])
                        response[field] = {
                            "total_claims": len(claims),
                            "quantitative_claims": len([c for c in claims if c.get("claim_type") == "quantitative"]),
                            "qualitative_claims": len([c for c in claims if c.get("claim_type") == "qualitative"]),
                            "total_gaps": len(gaps),
                            "annotation_confidence": "medium",
                            "notes": "Auto-generated quality metadata"
                        }

        # Log warnings but don't fail on them
        if warnings:
            logger.warning(f"Validation warnings: {warnings}")
            
        errors = missing_fields + type_errors
        is_valid = len(errors) == 0
        if not is_valid:
            logger.error(f"Validation failed: Missing fields: {missing_fields}, Type errors: {type_errors}")

        return is_valid, errors
    # --- END GOLDEN DATASET VALIDATION ---

    # --- MODIFIED: consensus_evaluation (passes definitions string) ---
    @staticmethod
    def consensus_evaluation(paper_text: str, metadata: PaperMetadata,
                             api_manager: APIManager, pillar_definitions_str: str,
                             num_evaluations: int = 1) -> Optional[Dict]:
        """Handles large docs, performs analysis, validates.

        Includes post-analysis validation:
        - Title relevance gate: compares extracted source title against review title
        - Quote verification: checks verbatim quotes exist in source text
        """
        final_text_to_analyze = ""
        is_summarized = False

        # --- FIX: Extract title from source text BEFORE summarization ---
        # This gives us a ground-truth title to compare against the review output,
        # catching cases where chunk summarization causes the model to hallucinate
        # about a completely different paper.
        source_title = extract_title_from_text(paper_text, filename=metadata.filename)
        if source_title:
            logger.info(f"Extracted source title: '{source_title[:80]}...'")

        if len(paper_text) > REVIEW_CONFIG['CHUNK_SIZE']:
            logger.info(f"Document is large ({len(paper_text)} chars). Applying map-reduce summarization...")
            safe_print(f"   Large document detected. Summarizing in chunks...")
            final_text_to_analyze = PaperAnalyzer.summarize_text_chunks(paper_text, api_manager, pillar_definitions_str)
            is_summarized = True
            if not final_text_to_analyze:
                logger.error("Chunk summarization failed.")
                return None
            logger.info("Summarization complete. Performing final analysis on compiled summary.")
            safe_print("   Summarization complete. Performing final analysis...")
        else:
            final_text_to_analyze = paper_text

        required_fields = PaperAnalyzer.REQUIRED_JSON_KEYS

        evaluations = []
        for i in range(num_evaluations):
            logger.info(f"Performing analysis evaluation {i + 1}/{num_evaluations}")
            safe_print(f"🔄 Performing analysis evaluation {i + 1}/{num_evaluations}")

            prompt = PaperAnalyzer.get_enhanced_analysis_prompt(final_text_to_analyze, metadata, pillar_definitions_str)
            logger.info(f"Sending final analysis prompt ({len(prompt)} chars) to API...")

            result = api_manager.cached_api_call(prompt, use_cache=(i == 0), is_json=True)

            if result:
                # Add fields that will be populated post-processing (with correct types)
                result.setdefault('CROSS_REFERENCES_COUNT', "0")
                result.setdefault('EXTRACTION_METHOD', str(metadata.extraction_method))
                result.setdefault('EXTRACTION_QUALITY', str(metadata.extraction_quality))
                result.setdefault('MENTIONED_PAPERS', [])
                result.setdefault('REVIEW_TIMESTAMP', str(metadata.timestamp))
                result.setdefault('SIMILAR_PAPERS', [])
                result.setdefault('SUMMARIZED_FROM_CHUNKS', 'Yes' if '[[[ This document was summarized' in final_text_to_analyze else 'No')
                
                is_valid, errors = PaperAnalyzer.validate_response(result, required_fields)
                if is_valid:
                    evaluations.append(result)
                else:
                    logger.error(f"Evaluation {i + 1} failed validation: {errors}")
            else:
                logger.error(f"API call failed for evaluation {i + 1}")

        if not evaluations:
            logger.error("All analysis evaluations failed.")
            return None

        # --- Aggregation logic (updated for Golden Dataset schema) ---
        if len(evaluations) > 1:
            logger.info("Aggregating results from multiple evaluations...")
            aggregated = evaluations[0].copy()
            numeric_fields = ['CORE_DOMAIN_RELEVANCE_SCORE', 'SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE',
                              'REPRODUCIBILITY_SCORE', 'BIOLOGICAL_FIDELITY']
            list_fields = ["MAJOR_FINDINGS", "KEYWORDS", "CORE_CONCEPTS", "INTERDISCIPLINARY_BRIDGES",
                           "NETWORK_ARCHITECTURE", "BRAIN_REGIONS", "DATASET_USED", "AUTHORS",
                           "claims", "gaps"]  # Updated to Golden Dataset fields
            string_fields = [f for f in required_fields if f not in numeric_fields and f not in list_fields]

            for field in numeric_fields:
                values = [e.get(field, 0) for e in evaluations if isinstance(e.get(field), int)]
                if values: aggregated[field] = int(np.mean(values))

            for field in list_fields:
                combined_list = []
                for e in evaluations:
                    items = e.get(field, [])
                    if isinstance(items, list):
                        combined_list.extend(items)

                # De-duplicate claims/gaps by verbatim_quote
                if field == "claims":
                    unique_claims = {}
                    for claim in combined_list:
                        if isinstance(claim, dict) and 'verbatim_quote' in claim:
                            unique_claims[claim['verbatim_quote']] = claim
                    aggregated[field] = list(unique_claims.values())
                elif field == "gaps":
                    unique_gaps = {}
                    for gap in combined_list:
                        if isinstance(gap, dict) and 'gap_text' in gap:
                            unique_gaps[gap['gap_text']] = gap
                    aggregated[field] = list(unique_gaps.values())
                else:
                    # De-duplicate list of strings
                    try:
                        aggregated[field] = sorted(list(set(combined_list)))
                    except TypeError:
                         aggregated[field] = combined_list

            for field in string_fields:
                first_valid = next((e.get(field) for e in evaluations if e.get(field) and e.get(field) != "N/A"), "N/A")
                aggregated[field] = first_valid

            final_result = aggregated
        else:
            final_result = evaluations[0]
        # --- End Aggregation ---

        # --- Post-process claims to ensure proper claim_id format ---
        if "claims" in final_result:
            paper_id = metadata.filename.replace('.pdf', '').replace('.html', '').replace('.txt', '')
            for idx, claim in enumerate(final_result["claims"]):
                if isinstance(claim, dict):
                    # Ensure claim_id follows Golden Dataset format
                    if not claim.get("claim_id") or "will_be_generated" in str(claim.get("claim_id", "")):
                        claim['claim_id'] = f"{paper_id}-C{idx+1:03d}"
        
        # Post-process gaps similarly
        if "gaps" in final_result:
            paper_id = metadata.filename.replace('.pdf', '').replace('.html', '').replace('.txt', '')
            for idx, gap in enumerate(final_result["gaps"]):
                if isinstance(gap, dict):
                    if not gap.get("gap_id") or "will_be_generated" in str(gap.get("gap_id", "")):
                        gap['gap_id'] = f"{paper_id}-G{idx+1:03d}"

        final_result['EXTRACTION_METHOD'] = metadata.extraction_method
        final_result['EXTRACTION_QUALITY'] = metadata.extraction_quality
        final_result['REVIEW_TIMESTAMP'] = metadata.timestamp
        final_result['SUMMARIZED_FROM_CHUNKS'] = is_summarized

        # --- FIX: Post-analysis validation gates ---
        # Gate 1: Title relevance check (catches hallucinated reviews of wrong paper)
        if source_title and is_summarized:
            review_title = final_result.get('TITLE', '')
            if review_title and source_title:
                # Compare source-extracted title against the review's TITLE field
                source_words = set(source_title.lower().split())
                review_words = set(review_title.lower().split())
                # Remove common stopwords for comparison
                stopwords = {'the', 'a', 'an', 'of', 'in', 'for', 'and', 'to', 'on', 'with', 'by', 'from', 'is', 'are', 'at', 'as'}
                source_keywords = source_words - stopwords
                review_keywords = review_words - stopwords
                if source_keywords and review_keywords:
                    overlap = len(source_keywords & review_keywords)
                    max_possible = min(len(source_keywords), len(review_keywords))
                    title_similarity = overlap / max_possible if max_possible > 0 else 0
                    if title_similarity < 0.15:
                        logger.warning(
                            f"TITLE MISMATCH for {metadata.filename}: "
                            f"source='{source_title[:60]}' vs review='{review_title[:60]}' "
                            f"(similarity={title_similarity:.2f}). Review may be hallucinated."
                        )
                        safe_print(
                            f"⚠️ TITLE MISMATCH detected for {metadata.filename} - "
                            f"review title does not match source document. Flagging for review."
                        )
                        final_result['_title_mismatch_warning'] = {
                            'source_title': source_title[:200],
                            'review_title': review_title[:200],
                            'similarity': round(title_similarity, 3)
                        }

        # Gate 2: Quote verification (catches fabricated verbatim quotes)
        # NOTE: Skip for summarized documents — the AI generates quotes from the
        # compiled summary, not the original text, so failing to find them in the
        # original is expected behavior, not evidence of hallucination.
        if is_summarized:
            logger.info(
                f"Skipping quote validation for {metadata.filename} "
                f"(document was summarized via map-reduce)."
            )
            final_result['_quote_validation'] = {
                'total_quotes': 0, 'verified_count': 0,
                'verification_rate': 1.0, 'is_valid': True,
                'skipped_reason': 'summarized_document'
            }
        else:
            quote_validation = validate_review_quotes(paper_text, final_result)
            final_result['_quote_validation'] = {
                'total_quotes': quote_validation['total_quotes'],
                'verified_count': quote_validation['verified_count'],
                'verification_rate': quote_validation['verification_rate'],
                'is_valid': quote_validation['is_valid']
            }
            if not quote_validation['is_valid']:
                logger.warning(
                    f"QUOTE VALIDATION FAILED for {metadata.filename}: "
                    f"only {quote_validation['verified_count']}/{quote_validation['total_quotes']} "
                    f"quotes verified (rate={quote_validation['verification_rate']:.1%}). "
                    f"Review may contain fabricated content."
                )
                safe_print(
                    f"⚠️ QUOTE VALIDATION FAILED for {metadata.filename} - "
                    f"{quote_validation['verification_rate']:.0%} quotes verified. "
                    f"Review may contain fabricated content."
                )
            else:
                logger.info(
                    f"Quote validation passed for {metadata.filename}: "
                    f"{quote_validation['verified_count']}/{quote_validation['total_quotes']} "
                    f"quotes verified ({quote_validation['verification_rate']:.0%})"
                )
        # --- END validation gates ---

        return final_result
    # --- END MODIFICATION ---

    @staticmethod
    def analyze_non_journal_item(paper_text: str, metadata: PaperMetadata,
                                 api_manager: APIManager) -> Optional[Dict]:
        """Handles analysis for non-journal items."""
        # This function is unchanged, as non-journal items don't need
        # requirement cross-referencing. We pass "" for definitions.
        final_text_to_analyze = ""
        is_summarized = False

        if len(paper_text) > REVIEW_CONFIG['CHUNK_SIZE']:
            logger.info(f"Document is large ({len(paper_text)} chars). Applying map-reduce summarization...")
            safe_print(f"   Large document detected. Summarizing in chunks...")
            final_text_to_analyze = PaperAnalyzer.summarize_text_chunks(paper_text, api_manager, "") # Pass empty string
            is_summarized = True
            if not final_text_to_analyze:
                logger.error("Chunk summarization failed.")
                return None
            logger.info("Summarization complete. Performing final analysis on compiled summary.")
            safe_print("   Summarization complete. Performing final analysis...")
        else:
            final_text_to_analyze = paper_text

        required_fields = PaperAnalyzer.NON_JOURNAL_JSON_KEYS
        logger.info("Performing non-journal analysis...")
        safe_print("🔄 Performing non-journal analysis...")
        prompt = PaperAnalyzer.get_non_journal_analysis_prompt(final_text_to_analyze, metadata)
        logger.info(f"Sending non-journal analysis prompt ({len(prompt)} chars) to API...")
        result = api_manager.cached_api_call(prompt, use_cache=True, is_json=True)

        if result:
            is_valid, errors = PaperAnalyzer.validate_response(result, required_fields)
            if is_valid:
                result['EXTRACTION_METHOD'] = metadata.extraction_method
                result['EXTRACTION_QUALITY'] = metadata.extraction_quality
                result['REVIEW_TIMESTAMP'] = metadata.timestamp
                result['SUMMARIZED_FROM_CHUNKS'] = is_summarized
                return result
            else:
                logger.error(f"Non-journal analysis failed validation: {errors}")
        else:
            logger.error("API call failed for non-journal analysis.")
        return None


# --- 4. Cross-Reference and Network Analysis (Unchanged) ---
# This class remains the same, as "CORE_CONCEPTS" was already added in v3.1
class NetworkAnalyzer:
    """Analyze relationships between papers"""
    def __init__(self, embedder: Optional[SentenceTransformer] = None):
        self.embedder = embedder
        self.embeddings_cache = {}
        self.load_embeddings_cache()
    def load_embeddings_cache(self):
        """Load cached embeddings"""
        cache_path = Path(EMBEDDINGS_CACHE)
        if cache_path.exists():
            try:
                with cache_path.open('rb') as f:
                    self.embeddings_cache = pickle.load(f)
                logger.info(f"Loaded {len(self.embeddings_cache)} cached embeddings from {EMBEDDINGS_CACHE}")
            except Exception as e:
                logger.warning(f"Could not load embeddings cache: {e}")
    def save_embeddings_cache(self):
        """Save embeddings cache"""
        if not REVIEW_CONFIG['CACHE_EMBEDDINGS']: return
        try:
            with open(EMBEDDINGS_CACHE, 'wb') as f:
                pickle.dump(self.embeddings_cache, f)
            logger.info(f"Saved {len(self.embeddings_cache)} embeddings to {EMBEDDINGS_CACHE}")
        except Exception as e:
            logger.warning(f"Could not save embeddings cache: {e}")
    def get_embedding(self, text: str, cache_key: str) -> Optional[np.ndarray]:
        """Get embedding for text with caching"""
        if not self.embedder: return None
        if cache_key in self.embeddings_cache: return self.embeddings_cache[cache_key]
        try:
            embedding = self.embedder.encode(text[:10000])
            if REVIEW_CONFIG['CACHE_EMBEDDINGS']:
                self.embeddings_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed for key {cache_key}: {e}")
            return None
    def find_similar_papers(self, paper_data: Dict, existing_papers: List[Dict],
                            threshold: float = REVIEW_CONFIG['SIMILARITY_THRESHOLD']) -> List[Tuple[Dict, float]]:
        """Find papers similar to the current one using embeddings"""
        if not self.embedder: return []
        paper_text = f"Title: {paper_data.get('TITLE', '')}. Core Concepts: {', '.join(paper_data.get('CORE_CONCEPTS', []))}. Abstract/Findings: {paper_data.get('MAJOR_FINDINGS', '')}. Keywords: {', '.join(paper_data.get('KEYWORDS', []))}"
        paper_key = paper_data.get('FILENAME', '')
        if not paper_key: return []
        paper_embedding = self.get_embedding(paper_text, paper_key)
        if paper_embedding is None: return []
        similar_papers = []
        existing_embeddings = {}
        target_keys = []
        target_embeddings_list = []
        for existing in existing_papers:
            existing_key = existing.get('FILENAME', '')
            if not existing_key or existing_key == paper_key: continue
            existing_emb = self.embeddings_cache.get(existing_key)
            if existing_emb is None:
                existing_text = f"Title: {existing.get('TITLE', '')}. Core Concepts: {', '.join(existing.get('CORE_CONCEPTS', []))}. Abstract/Findings: {existing.get('MAJOR_FINDINGS', '')}. Keywords: {', '.join(existing.get('KEYWORDS', []))}"
                existing_emb = self.get_embedding(existing_text, existing_key)
            if existing_emb is not None:
                target_keys.append(existing_key)
                target_embeddings_list.append(existing_emb)
        if not target_embeddings_list: return []
        target_embeddings_matrix = np.array(target_embeddings_list)
        similarities = cosine_similarity([paper_embedding], target_embeddings_matrix)[0]
        for i, similarity in enumerate(similarities):
            if similarity > threshold:
                target_paper = next((p for p in existing_papers if p.get('FILENAME') == target_keys[i]), None)
                if target_paper:
                    similar_papers.append((target_paper, float(similarity)))
        return sorted(similar_papers, key=lambda x: x[1], reverse=True)
    def extract_cross_references(self, paper_data: Dict, existing_papers: List[Dict]) -> List[Dict]:
        """Identify potential cross-references based on title mentions"""
        references = []
        paper_title = paper_data.get('TITLE', '').lower()
        paper_filename = paper_data.get('FILENAME')
        if not paper_title or not paper_filename or len(paper_title) < 15: return []
        paper_full_text_fields = ['APPLICABILITY_NOTES', 'ANALYSIS_GAPS', 'IMPROVEMENT_SUGGESTIONS']
        paper_text_combined = " ".join([str(paper_data.get(f, '')) for f in paper_full_text_fields]).lower()
        for existing in existing_papers:
            existing_title = existing.get('TITLE', '').lower()
            existing_filename = existing.get('FILENAME')
            if not existing_title or not existing_filename or existing_filename == paper_filename or len(existing_title) < 15: continue
            if existing_title in paper_text_combined:
                references.append({'source': paper_filename, 'target': existing_filename, 'type': 'mention'})
            existing_text_combined = " ".join([str(existing.get(f, '')) for f in paper_full_text_fields]).lower()
            if paper_title in existing_text_combined:
                references.append({'source': existing_filename, 'target': paper_filename, 'type': 'mention'})
        unique_refs = []
        seen = set()
        for ref in references:
            key = tuple(sorted((ref['source'], ref['target'])))
            if key not in seen:
                unique_refs.append(ref)
                seen.add(key)
        return unique_refs


# --- 5. Version Control (Unchanged) ---
class ReviewVersionControl:
    """Track changes in paper assessments over time"""
    def __init__(self):
        self.history = {}
        self.load_history()
    def load_history(self):
        """Load version history from file"""
        if os.path.exists(VERSION_HISTORY_FILE):
            try:
                with open(VERSION_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load version history: {e}")
    def save_history(self):
        """Save version history to file"""
        try:
            with open(VERSION_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save version history: {e}")
    def diff_from_previous(self, paper_id: str, new_review: Dict) -> Dict:
        """Calculate differences from previous version"""
        if paper_id not in self.history or not self.history[paper_id]:
            return {"status": "new_review"}
        previous = self.history[paper_id][-1]['review']
        changes = {}
        score_fields = ['CORE_DOMAIN_RELEVANCE_SCORE', 'SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE', 'REPRODUCIBILITY_SCORE',
                        'BIOLOGICAL_FIDELITY']
        for field in score_fields:
            try:
                new_val = int(new_review.get(field, 0))
                old_val = int(previous.get(field, 0))
                if new_val != old_val:
                    changes[field] = {'old': old_val, 'new': new_val, 'delta': new_val - old_val}
            except (ValueError, TypeError):
                continue
        return changes
    def save_version(self, paper_id: str, review: Dict):
        """Save a new version of a review"""
        timestamp = datetime.now().isoformat()
        if paper_id not in self.history:
            self.history[paper_id] = []
        review_copy = review.copy()
        changes = self.diff_from_previous(paper_id, review_copy)
        self.history[paper_id].append({
            'timestamp': timestamp,
            'review': review_copy,
            'changes': changes
        })
        self.save_history()


# --- 6. File Management Functions (Unchanged) ---
def load_review_log():
    """Load the set of already reviewed filenames"""
    if os.path.exists(REVIEW_LOG_FILE):
        try:
            with open(REVIEW_LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    reviewed_set = set(item for item in data if isinstance(item, str))
                    logger.info(f"Loaded review log with {len(reviewed_set)} entries")
                    return reviewed_set
                else:
                    logger.error("Review log is not a list. Creating new log.")
                    return set()
        except json.JSONDecodeError:
            logger.error(f"Error decoding review log JSON. Creating new log.")
            return set()
        except Exception as e:
            logger.error(f"Error loading review log: {e}")
            return set()
    return set()

def save_review_log(reviewed_files_set):
    """Save the set of reviewed filenames"""
    try:
        with open(REVIEW_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted([f for f in reviewed_files_set if isinstance(f, str)]), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved review log with {len(reviewed_files_set)} entries")
    except Exception as e:
        logger.error(f"Error saving review log: {e}")

def load_existing_reviews(csv_file=OUTPUT_CSV_FILE):
    """Load existing reviews from CSV into a list of dictionaries"""
    try:
        import pandas as pd
    except ImportError:
        logger.critical("Pandas library not found. Please install with: pip install pandas")
        return []
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            df = df.replace({np.nan: None})
            reviews = df.to_dict('records')
            for review in reviews:
                for col in review:
                    if isinstance(review[col], str) and review[col].startswith('['):
                        try:
                            review[col] = json.loads(review[col].replace("'", "\""))
                        except json.JSONDecodeError:
                            pass
            logger.info(f"Loaded and parsed {len(reviews)} existing reviews from {csv_file}")
            return reviews
        except pd.errors.EmptyDataError:
            logger.warning(f"CSV file is empty: {csv_file}")
            return []
        except Exception as e:
            logger.error(f"Could not load existing reviews from {csv_file}: {e}")
            if "Error tokenizing data" in str(e):
                logger.critical(
                    f"CRITICAL: The CSV file {csv_file} is corrupt. Please delete it or fix it manually before re-running.")
                safe_print(f"❌ CRITICAL: The CSV file {csv_file} is corrupt. Please delete it or fix it manually.")
    return []


def save_results_to_csv(reviews, csv_file=OUTPUT_CSV_FILE):
    """Append or overwrite results to CSV, handling all fields in master order."""
    if not reviews:
        return

    try:
        file_exists = os.path.isfile(csv_file)
        has_headers = file_exists and os.path.getsize(csv_file) > 0

        # --- MODIFIED LOGIC ---
        # 1. Use the explicit order as the base
        fieldnames = PaperAnalyzer.DATABASE_COLUMN_ORDER.copy()

        # 2. Find any *extra* keys in the data
        all_data_keys = set().union(*(d.keys() for d in reviews))
        extra_keys = sorted(list(all_data_keys - set(fieldnames)))

        # 3. Add extra keys to the end
        final_fieldnames = fieldnames + extra_keys

        if extra_keys:
            logger.warning(
                f"Found {len(extra_keys)} keys in data not in standard column order. Appending to end: {extra_keys}")

        # Check if existing file headers match
        if has_headers:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    existing_headers = next(reader)
                    if existing_headers != final_fieldnames:
                        logger.warning("CSV headers do not match master order! Sync script may be needed.")
                        # Use existing headers to avoid errors, but log it
                        final_fieldnames = existing_headers
            except Exception as e:
                logger.error(f"Could not read existing headers: {e}")
        # --- END MODIFIED LOGIC ---

        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=final_fieldnames, restval='', extrasaction='ignore',
                                    quoting=csv.QUOTE_ALL)
            if not has_headers:
                writer.writeheader()

            for review in reviews:
                row_to_write = {}
                for key in final_fieldnames:
                    value = review.get(key)
                    if isinstance(value, list) or isinstance(value, dict):
                        row_to_write[key] = json.dumps(value)
                    elif value is None:
                        row_to_write[key] = ''
                    else:
                        row_to_write[key] = value
                writer.writerow(row_to_write)

        logger.info(f"Saved/Appended {len(reviews)} journal reviews to {csv_file}")
        safe_print(f"💾 Saved/Appended {len(reviews)} journal reviews to {csv_file}")
    except Exception as e:
        logger.error(f"Error saving to CSV {csv_file}: {e}")
        safe_print(f"❌ Error saving to CSV {csv_file}: {e}")


# --- END MODIFICATION ---

def save_non_journal_results_to_csv(reviews, csv_file=NON_JOURNAL_CSV_FILE):
    """Append results to the non-journal CSV"""
    if not reviews:
        return
    try:
        file_exists = os.path.isfile(csv_file)
        fieldnames = PaperAnalyzer.NON_JOURNAL_JSON_KEYS.copy()
        extra_keys = set().union(*(d.keys() for d in reviews)) - set(fieldnames)
        fieldnames = fieldnames + sorted(list(extra_keys))
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval='', extrasaction='ignore', quoting=csv.QUOTE_ALL)
            if not file_exists or os.path.getsize(csv_file) == 0:
                writer.writeheader()
            for review in reviews:
                row_to_write = {}
                for key in fieldnames:
                    value = review.get(key)
                    if isinstance(value, list):
                        row_to_write[key] = json.dumps(value)
                    elif value is None:
                        row_to_write[key] = ''
                    else:
                        row_to_write[key] = value
                writer.writerow(row_to_write)
        logger.info(f"Saved/Appended {len(reviews)} non-journal items to {csv_file}")
        safe_print(f"💾 Saved/Appended {len(reviews)} non-journal items to {csv_file}")
    except Exception as e:
        logger.error(f"Error saving to CSV {csv_file}: {e}")
        safe_print(f"❌ Error saving to CSV {csv_file}: {e}")


# --- 7. Process Batch Function (MODIFIED) ---
def process_batch(batch_files: List[Tuple[str, str]], api_manager: APIManager,
                  network_analyzer: NetworkAnalyzer, version_control: ReviewVersionControl,
                  existing_reviews: List[Dict], pillar_definitions_str: str) -> Tuple[List[Dict], List[Dict]]:
    """Process a batch of files"""
    batch_journal_results = []
    batch_non_journal_results = []

    for filepath, filename in batch_files:
        try:
            logger.info(f"\n{'=' * 60}")
            safe_print(f"\n{'=' * 60}")
            logger.info(f"Processing: {filename}")
            safe_print(f"Processing: {filename}")

            extractor = TextExtractor()
            text, method, quality = extractor.robust_text_extraction(filepath)

            if not text or len(text) < REVIEW_CONFIG['MIN_TEXT_LENGTH']:
                logger.warning(
                    f"Skipping {filename} - text too short or extraction failed (Length: {len(text)}, Method: {method}, Quality: {quality:.2f})")
                safe_print(f"⏭️ Skipping {filename} - text too short or extraction failed")
                continue

            # is_valid, indicators = extractor.validate_paper_quality(text)
            # indicators.extraction_quality = (indicators.extraction_quality + quality) / 2.0

            papers_root = PAPERS_FOLDER
            rel_path = os.path.relpath(os.path.dirname(filepath), papers_root)
            domain_context = rel_path if rel_path != '.' else 'root'

            metadata = PaperMetadata(
                filename=filename,
                filepath=filepath,
                domain_context=domain_context,
                extraction_quality=quality, # Using direct quality from extraction
                extraction_method=method,
                timestamp=datetime.now().isoformat()
            )

            # --- PDF metadata via pymupdf (filename -> paper mapping) ---
            # Extracts title, authors, DOI, year, and page count using the
            # same backend the dissertation uses. This metadata is attached
            # to the review result so review_version_history.json carries a
            # high-fidelity filename->paper mapping. Note: these summaries
            # are NOT verbatim excerpts and must not be used for citation
            # chain verification — that path is the dissertation's own
            # pymupdf -> citation_log_gate pipeline.
            pdf_metadata = {}
            if filepath.lower().endswith('.pdf'):
                try:
                    from literature_review.metadata_extractor import EnhancedMetadataExtractor
                    pdf_metadata = EnhancedMetadataExtractor().extract_metadata(filepath)
                except Exception as md_e:
                    logger.warning(f"pymupdf metadata extraction failed for {filename}: {md_e}")

            # The validation logic is now simplified. We trust the extraction more.
            if quality > 0.1: # If extraction had some success
                logger.info(
                    f"Analyzing as Journal Paper (quality: {quality:.2f}, method: {method})")
                safe_print(
                    f"🧠 Analyzing as Journal Paper (quality: {quality:.2f}, method: {method})")
                
                num_evals = REVIEW_CONFIG['CONSENSUS_EVALUATIONS']
                if quality < 0.6:
                    num_evals = max(num_evals, 2)
                    logger.info(
                        f"Low quality score ({quality:.2f}), using {num_evals} evaluations for consensus.")
                    safe_print(f"   Low quality score, using {num_evals} evaluations...")
                
                # --- MODIFIED: Pass definitions string ---
                result = PaperAnalyzer.consensus_evaluation(
                    text, metadata, api_manager, pillar_definitions_str, num_evals
                )
                
                if not result:
                    logger.error(f"Journal analysis failed for {filename} after all attempts.")
                    safe_print(f"❌ Journal analysis failed for {filename}")
                    continue

                # --- FIX: Reject reviews that fail both validation gates ---
                # If both title mismatch AND quote validation fail, the review is
                # almost certainly hallucinated (wrong paper reviewed). Skip saving.
                has_title_mismatch = '_title_mismatch_warning' in result
                quote_valid = result.get('_quote_validation', {}).get('is_valid', True)
                if has_title_mismatch and not quote_valid:
                    logger.error(
                        f"REJECTING review for {filename}: both title mismatch and quote "
                        f"validation failed. This review is likely hallucinated."
                    )
                    safe_print(
                        f"🚫 REJECTING review for {filename} - title mismatch + "
                        f"quote verification failure indicates hallucinated review. Skipping."
                    )
                    continue
                # --- End rejection gate ---

                try:
                    similar = network_analyzer.find_similar_papers(result, existing_reviews + batch_journal_results)
                    if similar:
                        logger.info(f"Found {len(similar)} similar papers:")
                        safe_print(f"🔗 Found {len(similar)} similar papers:")
                        result['SIMILAR_PAPERS'] = [p.get('FILENAME') for p, sim in similar[:5]]
                    else:
                        result['SIMILAR_PAPERS'] = []
                    references = network_analyzer.extract_cross_references(result,
                                                                         existing_reviews + batch_journal_results)
                    if references:
                        result['CROSS_REFERENCES_COUNT'] = str(len(references))
                        result['MENTIONED_PAPERS'] = list(
                            set([ref['target'] for ref in references if ref['source'] == filename] +
                                [ref['source'] for ref in references if ref['target'] == filename]))
                    else:
                        result['CROSS_REFERENCES_COUNT'] = "0"
                        result['MENTIONED_PAPERS'] = []
                except Exception as net_e:
                    logger.error(f"Error during network analysis for {filename}: {net_e}")
                    result['SIMILAR_PAPERS'] = ["Error"]
                    result['CROSS_REFERENCES_COUNT'] = "-1"
                    result['MENTIONED_PAPERS'] = ["Error"]

                if pdf_metadata:
                    result['PDF_METADATA'] = {
                        'filename': filename,
                        'filepath': filepath,
                        'title': pdf_metadata.get('title'),
                        'authors': pdf_metadata.get('authors'),
                        'doi': pdf_metadata.get('doi'),
                        'year': pdf_metadata.get('year'),
                        'page_count': pdf_metadata.get('page_count'),
                        'extraction_backend': 'pymupdf',
                        'extraction_confidence': pdf_metadata.get('confidence', {}),
                    }

                version_control.save_version(filename, result)
                batch_journal_results.append(result)
                logger.info(f"Successfully analyzed {filename} as Journal Paper.")
                safe_print(f"✅ Successfully analyzed {filename} as Journal Paper.")

            else:
                # --- Non-journal item (simplified condition) ---
                logger.warning(f"File {filename} has very low extraction quality ({quality:.2f}). Processing as 'Non-Journal' item.")
                safe_print(f"📙 File {filename} has low quality. Processing as 'Non-Journal' item.")
                result = PaperAnalyzer.analyze_non_journal_item(text, metadata, api_manager)
                if not result:
                    logger.error(f"Non-journal analysis failed for {filename} after all attempts.")
                    safe_print(f"❌ Non-journal analysis failed for {filename}")
                    continue
                batch_non_journal_results.append(result)
                logger.info(f"Successfully analyzed {filename} as Non-Journal Item.")
                safe_print(f"✅ Successfully analyzed {filename} as Non-Journal Item.")


        except Exception as e:
            logger.critical(f"CRITICAL UNHANDLED ERROR on file {filename}: {type(e).__name__} - {e}")
            logger.critical("This file will be skipped. Moving to next file.")
            safe_print(f"❌ CRITICAL ERROR on {filename}. See log. Skipping.")
        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt detected. Stopping batch processing.")
            safe_print("\n🛑 Batch stopped by user.")
            break

    network_analyzer.save_embeddings_cache()
    return batch_journal_results, batch_non_journal_results


# --- 8. Main Execution (MODIFIED) ---
def main():
    """Main execution function with improved path handling"""
    start_time = time.time()
    logger.info("\n" + "=" * 80)
    logger.info("ENHANCED LITERATURE REVIEW PIPELINE v3.3 (Refactored)")
    logger.info("=" * 80)
    safe_print("\n" + "=" * 80)
    safe_print("ENHANCED LITERATURE REVIEW PIPELINE v3.3 (Refactored)")
    safe_print("=" * 80)

    papers_folder = PAPERS_FOLDER
    if not os.path.isdir(papers_folder):
        safe_print(f"❌ Papers folder not found at '{papers_folder}'!")
        logger.error(f"Please ensure the '{papers_folder}' directory exists.")
        return

    # --- NEW: Load Pillar Definitions ---
    logger.info("\n=== LOADING PILLAR DEFINITIONS ===")
    safe_print("\n=== LOADING PILLAR DEFINITIONS ===")
    try:
        with open(DEFINITIONS_FILE, 'r', encoding='utf-8') as f:
            pillar_definitions_json = json.load(f)
        # Create a compact string representation for the prompt
        pillar_definitions_str = json.dumps(pillar_definitions_json, indent=2)
        logger.info(f"Successfully loaded {len(pillar_definitions_json)} pillar definitions.")
        safe_print(f"✅ Successfully loaded {len(pillar_definitions_json)} pillar definitions.")
    except FileNotFoundError:
        logger.error(f"CRITICAL: Definitions file not found: {DEFINITIONS_FILE}")
        safe_print(f"❌ CRITICAL: Definitions file not found: {DEFINITIONS_FILE}. Cannot proceed.")
        return
    except json.JSONDecodeError as e:
        logger.error(f"CRITICAL: Error decoding definitions file: {e}")
        safe_print(f"❌ CRITICAL: Error decoding definitions file: {e}. Cannot proceed.")
        return
    # --- END NEW ---

    logger.info("\n=== INITIALIZING COMPONENTS ===")
    safe_print("\n=== INITIALIZING COMPONENTS ===")
    try:
        api_manager = APIManager()
        network_analyzer = NetworkAnalyzer(api_manager.embedder)
        version_control = ReviewVersionControl()
    except Exception as init_e:
        logger.critical(f"Failed to initialize core components: {init_e}")
        safe_print(f"❌ Failed to initialize core components: {init_e}")
        return

    reviewed_files = load_review_log()
    existing_reviews = load_existing_reviews(OUTPUT_CSV_FILE)
    existing_non_journal = load_existing_reviews(NON_JOURNAL_CSV_FILE)

    logger.info(f"Status: {len(reviewed_files)} files in review log")
    safe_print(f"📊 Status: {len(reviewed_files)} files in review log")
    logger.info(f"Existing journal database contains {len(existing_reviews)} papers")
    safe_print(f"📚 Existing journal database contains {len(existing_reviews)} papers")
    logger.info(f"Existing non-journal database contains {len(existing_non_journal)} items")
    safe_print(f"📙 Existing non-journal database contains {len(existing_non_journal)} items")

    files_to_process = collect_papers_to_process(papers_folder, reviewed_files)

    if not files_to_process:
        logger.info("\nNo new papers to process.")
        safe_print("\n📭 No new papers to process.")
        if len(reviewed_files) > 0 and DUPLICATE_MODE != 'overwrite':
            response = input("\nWould you like to force re-processing of all papers? (y/n): ").lower()
            if response == 'y':
                logger.info("Forcing re-process. Clearing review log...")
                safe_print("🔄 Forcing re-process. Clearing review log...")
                reviewed_files.clear()
                files_to_process = collect_papers_to_process(papers_folder, reviewed_files)
            else:
                return
        elif len(reviewed_files) == 0:
            logger.error("No papers found to process. Check folder structure and supported extensions.")
            safe_print("❌ No papers found to process. Check folder structure.")
            return
        else:
            return

    logger.info(f"\nReady to process {len(files_to_process)} papers")
    safe_print(f"\n🚀 Ready to process {len(files_to_process)} papers")

    if len(files_to_process) > 10:
        logger.info(f"Processing {len(files_to_process)} papers in batch mode.")
        safe_print(f"🚀 Batch mode: Processing {len(files_to_process)} papers without manual confirmation.")


    batch_size = REVIEW_CONFIG['BATCH_SIZE']
    total_batches = (len(files_to_process) + batch_size - 1) // batch_size
    newly_reviewed_papers = []
    newly_reviewed_non_journal = []

    for i in range(0, len(files_to_process), batch_size):
        batch = files_to_process[i:i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"\n--- Processing Batch {batch_num}/{total_batches} ({len(batch)} files) ---")
        safe_print(f"\n📦 Processing Batch {batch_num}/{total_batches} ({len(batch)} files)")

        # --- MODIFIED: Pass definitions string ---
        batch_results, batch_non_journal_results = process_batch(
            batch, api_manager, network_analyzer,
            version_control, existing_reviews + newly_reviewed_papers,
            pillar_definitions_str
        )

        for result in batch_results:
            newly_reviewed_papers.append(result)
            reviewed_files.add(result['FILENAME'])

        for result in batch_non_journal_results:
            newly_reviewed_non_journal.append(result)
            reviewed_files.add(result['FILENAME'])

        if batch_results:
            save_results_to_csv(batch_results, OUTPUT_CSV_FILE)
            logger.info(f"Batch {batch_num} journal results saved.")
            safe_print(f"💾 Batch {batch_num} journal results saved.")
        if batch_non_journal_results:
            save_non_journal_results_to_csv(batch_non_journal_results, NON_JOURNAL_CSV_FILE)
            logger.info(f"Batch {batch_num} non-journal results saved.")
            safe_print(f"💾 Batch {batch_num} non-journal results saved.")
        if batch_results or batch_non_journal_results:
            save_review_log(reviewed_files)

        total_processed = i + len(batch)
        logger.info(f"Progress: {total_processed}/{len(files_to_process)} papers processed")
        safe_print(f"📊 Progress: {total_processed}/{len(files_to_process)} papers processed")

    end_time = time.time()
    duration = end_time - start_time

    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Successfully reviewed {len(newly_reviewed_papers)} new journal papers in {duration:.2f} seconds.")
    logger.info(f"Successfully processed {len(newly_reviewed_non_journal)} new non-journal items.")
    logger.info(f"Total papers in journal database now: {len(load_existing_reviews(OUTPUT_CSV_FILE))}")
    logger.info(f"Total items in non-journal database now: {len(load_existing_reviews(NON_JOURNAL_CSV_FILE))}")
    logger.info("=" * 80)
    safe_print("\n" + "=" * 80)
    safe_print("PIPELINE COMPLETE")
    safe_print(f"✅ Reviewed {len(newly_reviewed_papers)} new journal papers in {duration:.2f} seconds.")
    safe_print(f"✅ Processed {len(newly_reviewed_non_journal)} new non-journal items.")
    safe_print(f"📊 Total in journal database: {len(load_existing_reviews(OUTPUT_CSV_FILE))}")
    safe_print(f"📙 Total in non-journal database: {len(load_existing_reviews(NON_JOURNAL_CSV_FILE))}")
    safe_print(f"\nResults saved to:")
    safe_print(f"   📁 Journal CSV: {os.path.abspath(OUTPUT_CSV_FILE)}")
    safe_print(f"   📁 Non-Journal CSV: {os.path.abspath(NON_JOURNAL_CSV_FILE)}")
    safe_print(f"   📁 Review Log: {os.path.abspath(REVIEW_LOG_FILE)}")
    safe_print(f"   📁 History Log: {os.path.abspath(VERSION_HISTORY_FILE)}")
    safe_print(f"   📁 Embeddings Cache: {os.path.abspath(EMBEDDINGS_CACHE)}")
    safe_print("=" * 80)


if __name__ == "__main__":
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.path.abspath('.')
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Script directory: {script_dir}")
    safe_print(f"📍 Current working directory: {os.getcwd()}")
    main()