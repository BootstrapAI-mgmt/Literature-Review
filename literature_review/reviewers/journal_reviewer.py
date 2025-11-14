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
import pypdf
import pdfplumber
import time
import hashlib
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
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
OUTPUT_CSV_FILE = 'neuromorphic-research_database.csv'
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
    "API_CALLS_PER_MINUTE": 60,
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

# --- NEW: Dataclass for Requirement Claims ---
@dataclass
class RequirementClaim:
    claim_id: str  # Hash(filename + sub_req + evidence)
    pillar: str
    sub_requirement: str
    evidence_chunk: str
    claim_summary: str # "why the reviewer thinks this requirement is covered"
    status: str      # 'pending_judge_review'

    def to_dict(self):
        return asdict(self)

def collect_papers_to_process(folder_path, reviewed_files):
    """Collect all papers that need processing"""
    files_to_process = []
    skipped_files = []
    logger.info("\n=== COLLECTING PAPERS TO PROCESS ===")
    safe_print("\n=== COLLECTING PAPERS TO PROCESS ===")
    
    # The folder_path is now 'data/raw', which contains 'Research-Papers'
    search_path = os.path.join(folder_path, 'Research-Papers')
    if not os.path.isdir(search_path):
        search_path = folder_path # Fallback to the base data/raw folder

    for root, dirs, files in os.walk(search_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
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
            files_to_process.append((filepath, filename))
            logger.debug(f"Added to process queue: {filename}")
            
    logger.info(f"\n📊 Summary:")
    safe_print(f"\n📊 Summary:")
    logger.info(f"   Total supported files found: {len(files_to_process) + len(skipped_files)}")
    safe_print(f"   Total supported files found: {len(files_to_process) + len(skipped_files)}")
    logger.info(f"   Already reviewed (skipped/kept): {len(skipped_files)}")
    safe_print(f"   Already reviewed (skipped/kept): {len(skipped_files)}")
    logger.info(f"   To be processed/reprocessed: {len(files_to_process)}")
    safe_print(f"   📋 To be processed/reprocessed: {len(files_to_process)}")
    return files_to_process


# --- 1. Initialize APIs and Models (Unchanged) ---
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
            self.json_generation_config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=1.0,
                top_k=1,
                max_output_tokens=16384,
                response_mime_type="application/json",
                thinking_config=thinking_config
            )
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
        if self.calls_this_minute >= REVIEW_CONFIG['API_CALLS_PER_MINUTE']:
            sleep_time = 60.1 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.info(
                    f"Rate limit ({REVIEW_CONFIG['API_CALLS_PER_MINUTE']}/min) reached. Sleeping for {sleep_time:.1f} seconds...")
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
        response_text = ""
        for attempt in range(REVIEW_CONFIG['RETRY_ATTEMPTS']):
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
                if attempt < REVIEW_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(REVIEW_CONFIG['RETRY_DELAY'])
                else:
                    logger.error("Max retries reached for JSON decode error.")
            except Exception as e:
                if "DeadlineExceeded" in str(e) or "Timeout" in str(e):
                    logger.error(f"API call timed out on attempt {attempt + 1}")
                else:
                    logger.error(f"API error on attempt {attempt + 1}: {type(e).__name__} - {e}")
                if "429" in str(e):
                    logger.warning("Rate limit error detected by API, increasing sleep time.")
                    time.sleep(REVIEW_CONFIG['RETRY_DELAY'] * (attempt + 2))
                elif attempt < REVIEW_CONFIG['RETRY_ATTEMPTS'] - 1:
                    time.sleep(REVIEW_CONFIG['RETRY_DELAY'])
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
            methods_to_try = [("pdfplumber", cls.extract_with_pdfplumber), ("pypdf", cls.extract_with_pypdf)]
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


def extract_text_with_provenance(file_path: str) -> List[Dict]:
    """
    Extract text with page-level tracking and section detection.
    
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
    - Page numbers
    - Section name
    - Character offsets
    - Supporting quote
    - Context before/after
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


# --- 3. Enhanced Analysis (MODIFIED) ---
class PaperAnalyzer:
    """Enhanced paper analysis with 'map-reduce' and requirement cross-referencing."""

    # --- MODIFIED: This is now the master column order ---
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
    # --- END MODIFICATION ---

    NON_JOURNAL_JSON_KEYS = [
        "FILENAME", "DOCUMENT_TYPE", "DETECTED_TOPICS", "KEY_CONCEPTS",
        "POTENTIAL_SEARCH_KEYWORDS", "SUMMARY_NOTES"
    ]

    # --- MODIFIED: Chunk prompt now needs to be aware of requirements ---
    @staticmethod
    def get_chunk_summary_prompt(chunk_text: str, chunk_num: int, total_chunks: int, pillar_definitions_str: str) -> str:
        """Creates a prompt to summarize a single chunk of a large document."""
        return f"""
You are a research summarization agent.
Your task is to read a chunk of a larger academic paper and extract its most critical information relevant to neuromorphic computing and brain-inspired AI.
This is CHUNK {chunk_num} of {total_chunks}.

Our core research interest is: "The mapping of human brain functions to machine learning frameworks, specifically in the areas of skill acquisition, memory consolidation, and stimulus-response, with emphasis on neuromorphic computing architectures."

--- KEY RESEARCH PILLARS (for context) ---
We are categorizing research into these pillars. Use these to guide your summary:
{pillar_definitions_str}
--- END PILLARS ---

Based ONLY on the text chunk provided below, extract and summarize:
1.  **Key Points:** Findings, methods, or conclusions relevant to our core research interest.
2.  **Potential Requirement Matches:** Any text that seems to *directly* address one of the sub-requirements listed in the pillar context.

Return your output as a concise, well-structured summary using bullet points.
Start immediately with the summary points.
Do not include introductory or concluding phrases.

--- TEXT CHUNK ---
{chunk_text}
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

        return f"""
You are an expert research assistant with deep knowledge in Machine Learning, Computational Neuroscience, and Cognitive Science.
Your task is to analyze an academic paper {'(provided as a compilation of chunk summaries)' if is_summarized else ''} and structure its key information for a master research database.

--- CORE RESEARCH TOPIC ---
"The mapping of human brain functions to machine learning frameworks, specifically in the areas of skill acquisition, memory consolidation, and stimulus-response, with emphasis on neuromorphic computing architectures."

--- FULL PILLAR DEFINITIONS (FOR CROSS-REFERENCE) ---
You *MUST* use this list to identify 'Requirement(s)' claims.
{pillar_definitions_str}
--- END PILLAR DEFINITIONS ---

Analyze the provided text below and return a single, clean JSON object.
Do not include any text, notes, or apologies before or after the JSON object.
Ensure all string values in the JSON are properly escaped.

The JSON object must contain these exact keys (use "N/A" or appropriate defaults like 0 or [] if information is not found):
- "TITLE": (String) The full title of the paper. Infer if necessary.
- "CORE_DOMAIN": (String) Primary field (e.g., "Machine Learning", "Neuroscience", "Neuromorphic Engineering").
- "SUB_DOMAIN": (String) Specific sub-field (e.g., "Reinforcement Learning", "Spiking Neural Networks").
- "CORE_DOMAIN_RELEVANCE_SCORE": (Integer 0-100) Paper's depth/quality within its core domain.
- "SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE": (Integer 0-100) Relevance of the SUB_DOMAIN to *our* core research topic.
- "MAJOR_FINDINGS": (List of Strings) 2-4 bullet points summarizing key results/conclusions.
- "APPLICABILITY_NOTES": (String) How findings could apply to our research.
- "ANALYSIS_GAPS": (String) Gaps or limitations noted in the paper.
- "IMPROVEMENT_SUGGESTIONS": (String) Suggestions for extending the study.
- "SOURCE": (String) Journal, conference, or website.
- "PUBLICATION_YEAR": (Integer or "N/A") Year of publication.
- "APA_REFERENCE": (String) Best attempt at APA 7th edition reference.
- "FULL_TEXT_LINK": (String) DOI or URL found in text, otherwise "N/A".
- "FILENAME": "{metadata.filename}" (String)
- "KEYWORDS": (List of Strings) 5-10 *author-provided* keywords.
- "CORE_CONCEPTS": (List of Strings) 5-10 *AI-generated* fundamental concepts (e.g., "Hebbian Learning", "STDP").
- "RISKS": (String) Potential challenges or risks highlighted.
- "MATURITY_LEVEL": (String) Estimate maturity (e.g., "Theoretical", "Experimental", "Applied").
- "REPRODUCIBILITY_SCORE": (Integer 0-100) Estimate based on methods detail.
- "INTERDISCIPLINARY_BRIDGES": (List of Strings) Specific concepts linking AI/Neuroscience.
- "IMPLEMENTATION_DETAILS": (String) Note presence of code, algorithms, hardware specs.
- "VALIDATION_METHOD": (String) How findings were validated (e.g., "Simulation", "Benchmark Dataset").
- "SCALABILITY_NOTES": (String) Mention of scalability issues or potential.
- "ENERGY_EFFICIENCY": (String) Mention of power consumption.
- "BIOLOGICAL_FIDELITY": (Integer 0-100) How closely the model mimics biology.
- "NETWORK_ARCHITECTURE": (List of Strings) Specific architectures (e.g., "CNN", "SNN").
- "BRAIN_REGIONS": (List of Strings) Specific brain regions (e.g., "Hippocampus").
- "COMPUTATIONAL_COMPLEXITY": (String) Mention of complexity analysis.
- "DATASET_USED": (List of Strings) Datasets used (e.g., "MNIST").

- "Requirement(s)": (List of Objects)
  - This is the most critical new field.
  - Scan the paper for any text that *directly provides evidence* for any sub-requirement listed in the "FULL PILLAR DEFINITIONS".
  - For *each* piece of evidence found, create one object in this list.
  - If no evidence is found for any requirement, return an empty list [].
  - Each object in the list *must* have this structure:
    {{
      "claim_id": "will_be_generated_later",
      "pillar": "(String) The **EXACT, VERBATIM** pillar name from the definitions (e.g., 'Pillar 1: Foundational Concepts').",
      "sub_requirement": "(String) The **EXACT, VERBATIM** sub-requirement string from the definitions (e.g., 'SR1.1: Define and model core components...').",
      "evidence_chunk": "(String) The *exact* 1-3 sentences from the paper text that support the claim.",
      "claim_summary": "(String) Your 1-sentence explanation of *why* this chunk covers the requirement.",
      "status": "pending_judge_review"
    }}

{'--- START OF TEXT ---' if not is_summarized else '--- START OF COMPILED SUMMARIES ---'}
{paper_text}
{'--- END OF TEXT ---' if not is_summarized else '--- END OF COMPILED SUMMARIES ---'}
"""
    # --- END MODIFICATION ---

    @staticmethod
    def get_non_journal_analysis_prompt(paper_text: str, metadata: PaperMetadata) -> str:
        """Generate a simpler analysis prompt for non-journal items like lecture slides."""
        is_summarized = "[[[ This document was summarized" in paper_text[:500]
        return f"""
You are a research assistant.
Your task is to analyze a document that is likely NOT a formal academic paper (e.g., lecture slides, notes, a web article).
Your goal is to extract key topics and search terms that could be useful for finding actual journal papers later.
Our core research topic is: "The mapping of human brain functions to machine learning frameworks, specifically in the areas of skill acquisition, memory consolidation, and stimulus-response, with emphasis on neuromorphic computing architectures."
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
{paper_text}
{'--- END OF TEXT ---' if not is_summarized else '--- END OF COMPILED SUMMARIES ---'}
"""

    # --- MODIFIED: validate_response ---
    @staticmethod
    def validate_response(response: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate AI response, sanitize common type mismatches (str -> list)"""
        missing_fields = []
        type_errors = []
        if not isinstance(response, dict):
            return False, ["Response is not a valid JSON object"]

        for field in required_fields:
            if field not in response:
                missing_fields.append(field)
                continue

            value = response[field]
            expected_type = None

            # Check types based on which set of keys we are using
            if field in PaperAnalyzer.DATABASE_COLUMN_ORDER:  # Use master list
                if field.endswith("_SCORE") or field == "BIOLOGICAL_FIDELITY":
                    expected_type = int
                elif field == "PUBLICATION_YEAR":
                    expected_type = "Int_or_NA"
                elif field in ["MAJOR_FINDINGS", "KEYWORDS", "CORE_CONCEPTS", "INTERDISCIPLINARY_BRIDGES",
                               "NETWORK_ARCHITECTURE", "BRAIN_REGIONS", "DATASET_USED",
                               "SIMILAR_PAPERS", "MENTIONED_PAPERS"]:  # Added missing list fields
                    expected_type = "list_of_str"
                elif field == "Requirement(s)":
                    expected_type = "list_of_obj"
                else:
                    expected_type = "str"

            elif field in PaperAnalyzer.NON_JOURNAL_JSON_KEYS:
                # (identical logic for non-journal keys)
                if field in ["DETECTED_TOPICS", "KEY_CONCEPTS", "POTENTIAL_SEARCH_KEYWORDS"]:
                    expected_type = "list_of_str"
                else:
                    expected_type = "str"

            # --- Sanitization and Type Checking ---
            if expected_type == "list_of_str" and isinstance(value, str):
                logger.warning(f"Sanitizing field '{field}': converting string '{value}' to list.")
                response[field] = [value]
                value = response[field]

            if expected_type == int and not isinstance(value, int):
                type_errors.append(f"Field '{field}' expected Integer, got {type(value)}")
            elif expected_type == "Int_or_NA" and not (isinstance(value, int) or value == "N/A"):
                type_errors.append(f"Field '{field}' expected Integer or 'N/A', got {type(value)}")
            elif expected_type == "list_of_str" and not isinstance(value, list):
                type_errors.append(f"Field '{field}' expected List, got {type(value)}")
            elif expected_type == "list_of_str" and value and not all(isinstance(item, str) for item in value):
                try:
                    response[field] = [str(item) for item in value]
                    logger.warning(f"Sanitizing field '{field}': converting list items to string.")
                except Exception:
                    type_errors.append(f"Field '{field}' expected List of Strings, but items are not all strings.")
            elif expected_type == "str" and not isinstance(value, str):
                type_errors.append(f"Field '{field}' expected String, got {type(value)}")

            # --- NEW: Validate list_of_obj for "Requirement(s)" ---
            elif expected_type == "list_of_obj":
                if not isinstance(value, list):
                    type_errors.append(f"Field '{field}' expected List of Objects, got {type(value)}")
                elif value: # If list is not empty, check first item
                    first_item = value[0]
                    if not (isinstance(first_item, dict) and
                            'pillar' in first_item and
                            'sub_requirement' in first_item and
                            'evidence_chunk' in first_item and
                            'claim_summary' in first_item):
                        type_errors.append(f"Field '{field}' items have incorrect structure.")

        errors = missing_fields + type_errors
        is_valid = len(errors) == 0
        if not is_valid:
            logger.error(f"Validation failed: Missing fields: {missing_fields}, Type errors: {type_errors}")

        return is_valid, errors

    # --- END MODIFICATION ---

    # --- MODIFIED: consensus_evaluation (passes definitions string) ---
    @staticmethod
    def consensus_evaluation(paper_text: str, metadata: PaperMetadata,
                             api_manager: APIManager, pillar_definitions_str: str,
                             num_evaluations: int = 1) -> Optional[Dict]:
        """Handles large docs, performs analysis, validates."""
        final_text_to_analyze = ""
        is_summarized = False

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

        # --- Aggregation logic (unchanged, but now includes "Requirement(s)") ---
        if len(evaluations) > 1:
            logger.info("Aggregating results from multiple evaluations...")
            aggregated = evaluations[0].copy()
            numeric_fields = ['CORE_DOMAIN_RELEVANCE_SCORE', 'SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE',
                              'REPRODUCIBILITY_SCORE', 'BIOLOGICAL_FIDELITY']
            list_fields = ["MAJOR_FINDINGS", "KEYWORDS", "CORE_CONCEPTS", "INTERDISCIPLINARY_BRIDGES",
                           "NETWORK_ARCHITECTURE", "BRAIN_REGIONS", "DATASET_USED",
                           "Requirement(s)"] # <-- Added new field
            string_fields = [f for f in required_fields if f not in numeric_fields and f not in list_fields]

            for field in numeric_fields:
                values = [e.get(field, 0) for e in evaluations if isinstance(e.get(field), int)]
                if values: aggregated[field] = int(np.mean(values))

            for field in list_fields:
                combined_list = []
                for e in evaluations:
                    items = e.get(field, [])
                    if isinstance(items, list):
                        # Simple extension for lists of strings/objects
                        combined_list.extend(items)

                # De-duplicate. For "Requirement(s)", we need a smarter way
                if field == "Requirement(s)":
                    unique_claims = {}
                    for claim in combined_list:
                        if isinstance(claim, dict) and 'evidence_chunk' in claim:
                            # Use evidence_chunk as a simple de-dupe key
                            unique_claims[claim['evidence_chunk']] = claim
                    aggregated[field] = list(unique_claims.values())
                else:
                    # De-duplicate list of strings
                    try:
                        aggregated[field] = sorted(list(set(combined_list)))
                    except TypeError: # Fails if list contains dicts, but we handled that
                         aggregated[field] = combined_list

            for field in string_fields:
                first_valid = next((e.get(field) for e in evaluations if e.get(field) and e.get(field) != "N/A"), "N/A")
                aggregated[field] = first_valid

            final_result = aggregated
        else:
            final_result = evaluations[0]
        # --- End Aggregation ---

        # --- NEW: Post-process Requirement(s) to add claim_id ---
        if "Requirement(s)" in final_result:
            for claim in final_result["Requirement(s)"]:
                if isinstance(claim, dict) and claim.get("claim_id") == "will_be_generated_later":
                    try:
                        claim_hash = hashlib.md5(f"{metadata.filename}{claim['sub_requirement']}{claim['evidence_chunk']}".encode('utf-8')).hexdigest()
                        claim['claim_id'] = claim_hash
                    except Exception as e:
                        logger.warning(f"Could not generate claim_id: {e}")
                        claim['claim_id'] = "generation_failed"

        final_result['EXTRACTION_METHOD'] = metadata.extraction_method
        final_result['EXTRACTION_QUALITY'] = metadata.extraction_quality
        final_result['REVIEW_TIMESTAMP'] = metadata.timestamp
        final_result['SUMMARIZED_FROM_CHUNKS'] = is_summarized

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
                # --- End Modification ---

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
                        result['CROSS_REFERENCES_COUNT'] = len(references)
                        result['MENTIONED_PAPERS'] = list(
                            set([ref['target'] for ref in references if ref['source'] == filename] +
                                [ref['source'] for ref in references if ref['target'] == filename]))
                    else:
                        result['CROSS_REFERENCES_COUNT'] = 0
                        result['MENTIONED_PAPERS'] = []
                except Exception as net_e:
                    logger.error(f"Error during network analysis for {filename}: {net_e}")
                    result['SIMILAR_PAPERS'] = ["Error"]
                    result['CROSS_REFERENCES_COUNT'] = -1
                    result['MENTIONED_PAPERS'] = ["Error"]

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
        response = input(
            f"This will process {len(files_to_process)} papers. This may take time and cost money. Continue? (y/n): ").lower()
        if response != 'y':
            logger.info("Processing cancelled by user")
            safe_print("❌ Processing cancelled by user")
            return

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