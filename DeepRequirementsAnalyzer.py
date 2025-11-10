"""
Deep Requirements Analyzer (DRA)
Version: 1.1 (Batches claims by document for efficiency)
Date: 2025-11-09

This module is called by the 'Judge' script. It takes claims that
the Judge has rejected, groups them by their source document,
and re-reads each document *only once*.

It performs a deeper AI-driven search to find better evidence for
*all* rejected claims from that document in a single API call.
"""

import os
import sys
import json
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
import logging
from collections import defaultdict # <-- NEW: For grouping claims

# --- CONFIGURATION (Copied from Journal-Reviewer) ---
# This is needed to find the source documents
PAPERS_FOLDER = r'C:\Users\jpcol\OneDrive\Documents\Doctorate\Research\Literature-Review'
ALTERNATIVE_PATHS = [
    r'C:\Users\jpcol\Documents\Doctorate\Research\Literature-Review',
    r'C:\Users\jpcol\OneDrive\Documents\Research\Literature-Review',
    r'.\Literature-Review',
    r'..\Literature-Review',
]
REVIEW_CONFIG = {
    "MIN_TEXT_LENGTH": 500,
    "DRA_CHUNK_SIZE": 50000,  # Chunk size for DRA text processing
}

# --- Logging ---
logger = logging.getLogger(__name__)

# --- DEFINITIONS FILE ---
DEFINITIONS_FILE = 'pillar_definitions_enhanced.json'


def safe_print(message):
    """Print message safely handling Unicode on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(str(message).encode(sys.stdout.encoding or 'utf-8', 'replace').decode(sys.stdout.encoding or 'utf-8'))


def load_pillar_definitions(filepath: str) -> Dict:
    """Load pillar definitions for DRA analysis."""
    if not os.path.exists(filepath):
        logger.error(f"Pillar definitions file not found: {filepath}")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading pillar definitions: {e}")
        return {}


def find_sub_requirement_definition(definitions: Dict, pillar_key: str, 
                                     sub_req_key: str) -> Optional[str]:
    """Extract the full definition text for a sub-requirement."""
    for pillar_name, pillar_data in definitions.items():
        if pillar_name == pillar_key or pillar_name.startswith(pillar_key):
            for req_key, sub_req_list in pillar_data.get('requirements', {}).items():
                for sub_req_text in sub_req_list:
                    if sub_req_text == sub_req_key or sub_req_text.startswith(sub_req_key):
                        return sub_req_text
    return None


# --- TextExtractor CLASS (Unchanged) ---
# ... (Full class code omitted for brevity) ...
class TextExtractor:
    """Robust text extraction from multiple file formats"""
    @staticmethod
    def extract_with_pypdf(filepath: str) -> Tuple[str, float]:
        text, quality, page_count = "", 0.0, 0
        try:
            with open(filepath, 'rb') as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                if page_count == 0: return "", 0.0
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
        text, quality, page_count = "", 0.0, 0
        try:
            with pdfplumber.open(filepath) as pdf:
                page_count = len(pdf.pages)
                if page_count == 0: return "", 0.0
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
                    text, quality, method = "", 0.0, "failed_decode"
            except Exception as e:
                text, quality, method = "", 0.0, "failed_read"
        else:
            logger.warning(f"Unsupported file type: {filepath}")
        return text, method, quality
# --- END TextExtractor CLASS ---


# --- Path Diagnostic Functions (Unchanged) ---
# ... (Full functions omitted for brevity) ...
def find_papers_folder():
    if os.path.exists(PAPERS_FOLDER) and os.path.isdir(PAPERS_FOLDER):
        logger.info(f"Using primary PAPERS_FOLDER: {PAPERS_FOLDER}")
        return PAPERS_FOLDER
    for alt_path in ALTERNATIVE_PATHS:
        abs_path = os.path.abspath(alt_path)
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            logger.info(f"Found papers folder at alternative location: {abs_path}")
            return abs_path
    # ... (rest of fallback logic) ...
    logger.error("Could not find papers folder in any specified location.")
    return None

def find_paper_filepath(filename: str, papers_folder: str) -> Optional[str]:
    for root, dirs, files in os.walk(papers_folder):
        if filename in files:
            return os.path.join(root, filename)
    logger.warning(f"Could not find file: {filename} in {papers_folder}")
    return None
# --- END Path Functions ---


# --- CHUNKING FUNCTIONS ---

def chunk_text_with_page_tracking(full_text: str, chunk_size: int = 50000) -> List[Tuple[str, str]]:
    """
    Split large text into chunks while tracking page ranges.
    Returns list of tuples: (chunk_text, page_range_str)
    """
    if len(full_text) <= chunk_size:
        # Extract page range from the text
        page_range = extract_page_range(full_text)
        return [(full_text, page_range)]
    
    # Add 10% overlap for context preservation
    overlap = int(chunk_size * 0.1)
    chunks = []
    
    for i in range(0, len(full_text), chunk_size - overlap):
        chunk_text = full_text[i:i + chunk_size]
        page_range = extract_page_range(chunk_text)
        chunks.append((chunk_text, page_range))
    
    logger.info(f"DRA: Split text ({len(full_text)} chars) into {len(chunks)} chunks")
    return chunks


def extract_page_range(text: str) -> str:
    """
    Extract page range from text that contains page markers like '--- Page N ---'.
    Returns a string like "Pages 1-5" or "Page 1" or "N/A".
    """
    import re
    
    # Find all page markers in the format "--- Page N ---"
    page_markers = re.findall(r'---\s*Page\s+(\d+)\s*---', text)
    
    if not page_markers:
        return "N/A"
    
    page_numbers = sorted([int(p) for p in page_markers])
    
    if len(page_numbers) == 1:
        return f"Page {page_numbers[0]}"
    else:
        return f"Pages {page_numbers[0]}-{page_numbers[-1]}"


def aggregate_chunk_results(chunk_results: List[Dict]) -> List[Dict]:
    """
    Aggregate results from multiple chunks, removing duplicates.
    Each chunk_result should have a 'new_claims_to_rejudge' key.
    """
    all_claims = []
    seen_evidence = set()
    
    for chunk_result in chunk_results:
        new_claims = chunk_result.get('new_claims_to_rejudge', [])
        for claim in new_claims:
            # Use evidence_chunk as deduplication key
            evidence = claim.get('evidence_chunk', '')
            # Simple deduplication: if we've seen similar evidence, skip
            if evidence and evidence not in seen_evidence:
                all_claims.append(claim)
                seen_evidence.add(evidence)
    
    logger.info(f"DRA: Aggregated {len(all_claims)} unique claims from {len(chunk_results)} chunks")
    return all_claims


# --- END CHUNKING FUNCTIONS ---


# --- CORE LOGIC (MODIFIED) ---

def build_dra_prompt(claims_for_document: List[Dict], full_paper_text: str,
                     pillar_definitions: Dict, page_range: str = "N/A") -> str:
    """
    Builds the prompt for the Deep Requirements Analyzer AI.
    This prompt includes *all* rejected claims for a single document.
    Now includes pillar_definitions (from PR #2) and page_range (from PR #3).
    """

    rejection_list_str = ""
    for i, claim in enumerate(claims_for_document, 1):
        # NEW: Get the canonical definition
        pillar_key = claim.get('pillar', 'N/A')
        sub_req_key = claim.get('sub_requirement', 'N/A')
        definition_text = find_sub_requirement_definition(
            pillar_definitions, pillar_key, sub_req_key
        )
        
        rejection_list_str += f"""
--- REJECTED CLAIM #{i} ---
Pillar: {pillar_key}
Sub-Requirement Key: {sub_req_key}
FULL REQUIREMENT DEFINITION ("THE LAW"):
"{definition_text if definition_text else 'NOT FOUND - Cannot satisfy this claim!'}"

Judge's Rejection Reason: "{claim.get('judge_notes', 'N/A')}"
Original Evidence Provided: "{claim.get('evidence_chunk', 'N/A')}"
(Internal Claim ID: {claim.get('claim_id')})
"""

    return f"""
You are an expert "Deep Requirements Analyzer." Your task is to re-evaluate a list of claims that were rejected by an impartial Judge. You will find *better* evidence for *all* of them from the full text of the single paper provided.

**NOTE:** You are analyzing {page_range} of this document. Focus on evidence within this section.

--- CRITICAL INSTRUCTIONS ---
1. The "FULL REQUIREMENT DEFINITION" shown for each rejected claim is the EXACT text that the Judge will validate against.
2. Your evidence MUST DIRECTLY and EXPLICITLY satisfy that FULL definition, NOT just the sub-requirement key.
3. The Judge rejected the original attempt for specific reasons. Your new evidence must ADDRESS those reasons.
4. Quote text EXACTLY from the paper. The Judge will verify your quotes.
5. If you cannot find text that CLEARLY satisfies the FULL definition, DO NOT submit a claim for that requirement.

--- LIST OF REJECTED CLAIMS ---
{rejection_list_str}
--- END OF LIST ---

--- YOUR TASK ---
1.  **Understand "THE LAW":** For each rejected claim, carefully read the FULL REQUIREMENT DEFINITION.
2.  **Understand the Rejection:** Read why the Judge rejected the original evidence.
3.  **Scan the FULL TEXT:** Read the entire document provided below.
4.  **Find Direct Evidence:** For each rejected claim, locate text that:
    - DIRECTLY addresses the FULL REQUIREMENT DEFINITION
    - Overcomes the Judge's specific rejection reason
    - Is EXPLICIT, not implied or tangential
5.  **Be Selective:** Only submit claims where you have HIGH confidence (>0.9) that the new evidence will satisfy the Judge.

--- Output Format ---
Return ONLY a JSON object with a single key, "new_claims_to_rejudge", which is a list.
For *each* rejected claim you were able to find *new, better* evidence for, return a new claim object in the list.

Example:
{{
  "new_claims_to_rejudge": [
    {{
      "original_claim_id": "(String) The 'Internal Claim ID' of the rejected claim.",
      "claim_summary": "(String) A 1-sentence argument for why this evidence NOW satisfies the FULL definition AND addresses the rejection.",
      "evidence_chunk": "(String) EXACT quote from paper. Can be multiple paragraphs if needed for completeness.",
      "reviewer_confidence": 0.95
    }}
  ]
}}

If no new, high-quality evidence is found for *any* of the rejected claims, return an empty list:
{{
  "new_claims_to_rejudge": []
}}

--- FULL PAPER TEXT ---
{full_paper_text}
--- END FULL PAPER TEXT ---
"""


def run_analysis(
        rejected_claims: List[Dict],
        api_manager: Any,
        papers_folder_path: str
) -> List[Dict]:
    """
    Main entry point for the DRA.
    Takes a list of rejected claims, **groups them by document**,
    re-scans each source file *once*, and returns a list of new,
    improved claims for re-judgment.
    """

    if not papers_folder_path:
        logger.error("DRA: Cannot run analysis, papers folder path is not set.")
        return []

    # NEW: Load pillar definitions
    pillar_definitions = load_pillar_definitions(DEFINITIONS_FILE)
    if not pillar_definitions:
        logger.error("DRA: Cannot proceed without pillar definitions.")
        return []

    text_extractor = TextExtractor()
    new_claims_for_rejudgment = []

    # --- NEW: Group claims by filename ---
    claims_by_file = defaultdict(list)
    for claim in rejected_claims:
        filename = claim.get('filename') or claim.get('_filename', 'N/A')
        if filename:
            claims_by_file[filename].append(claim)
    # --- END NEW ---

    logger.info(f"DRA: Received {len(rejected_claims)} rejected claims, grouped into {len(claims_by_file)} documents for analysis.")
    safe_print(f"DRA: Analyzing {len(rejected_claims)} rejected claims across {len(claims_by_file)} documents.")

    # --- NEW: Loop through each DOCUMENT, not each claim ---
    for i, (filename, claims_for_doc) in enumerate(claims_by_file.items(), 1):

        safe_print(f"  DRA: Analyzing Document {i}/{len(claims_by_file)}: {filename[:30]}... ({len(claims_for_doc)} rejected claims)")

        if not filename:
            logger.warning("DRA: Skipping claim group, missing filename.")
            continue

        # 1. Find and read the full paper text (ONCE per document)
        filepath = find_paper_filepath(filename, papers_folder_path)
        if not filepath:
            logger.error(f"DRA: Could not find source file {filename}. Skipping all {len(claims_for_doc)} claims for this doc.")
            continue

        full_text, _, _ = text_extractor.robust_text_extraction(filepath)
        if not full_text:
            logger.error(f"DRA: Could not extract text from {filename}. Skipping all {len(claims_for_doc)} claims.")
            continue

        # 2. Check if text needs chunking
        if len(full_text) > REVIEW_CONFIG['DRA_CHUNK_SIZE']:
            logger.info(f"DRA: Document is large ({len(full_text)} chars). Chunking at {REVIEW_CONFIG['DRA_CHUNK_SIZE']} chars.")
            safe_print(f"    DRA: Large document detected. Processing in chunks...")
            
            # Chunk the text with page tracking
            text_chunks = chunk_text_with_page_tracking(full_text, REVIEW_CONFIG['DRA_CHUNK_SIZE'])
            chunk_results = []
            
            # Process each chunk
            for chunk_num, (chunk_text, page_range) in enumerate(text_chunks, 1):
                logger.info(f"DRA: Processing chunk {chunk_num}/{len(text_chunks)} ({page_range})")
                safe_print(f"    DRA: Processing chunk {chunk_num}/{len(text_chunks)} ({page_range})")
                
                # Build prompt for this chunk (with pillar_definitions AND page_range)
                prompt = build_dra_prompt(claims_for_doc, chunk_text, pillar_definitions, page_range)
                
                try:
                    # Call API for this chunk
                    chunk_response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
                    
                    if chunk_response and "new_claims_to_rejudge" in chunk_response:
                        chunk_results.append(chunk_response)
                        logger.info(f"DRA: Chunk {chunk_num} returned {len(chunk_response.get('new_claims_to_rejudge', []))} potential claims")
                    else:
                        logger.warning(f"DRA: Chunk {chunk_num} returned invalid response")
                        
                except Exception as e:
                    logger.error(f"DRA: Error processing chunk {chunk_num}: {e}")
            
            # Aggregate results from all chunks
            if chunk_results:
                aggregated_claims = aggregate_chunk_results(chunk_results)
                # Create a synthetic response with aggregated claims
                ai_response = {"new_claims_to_rejudge": aggregated_claims}
                logger.info(f"DRA: Aggregated {len(aggregated_claims)} unique claims from {len(chunk_results)} chunks")
            else:
                ai_response = {"new_claims_to_rejudge": []}
                logger.warning(f"DRA: No valid chunk results for {filename}")
        else:
            # Document is small enough, process normally
            # Build the prompt with ALL claims for this doc + definitions + page range
            prompt = build_dra_prompt(claims_for_doc, full_text, pillar_definitions, "Full Document")

            # 3. Call API (no cache, always re-analyze)
            try:
                ai_response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
            except Exception as e:
                logger.error(f"DRA: Error calling API for {filename}: {e}")
                ai_response = None

        # 4. Process the response (same for chunked and non-chunked)
        try:
            if not ai_response or "new_claims_to_rejudge" not in ai_response:
                logger.error(f"DRA: AI response was invalid for {filename}.")
                continue

            new_claims_list = ai_response.get("new_claims_to_rejudge")
            if not new_claims_list:
                logger.info(f"DRA: No new high-confidence evidence found for any claims in {filename}.")
                safe_print("    DRA: No new evidence found.")
                continue

            # --- NEW: Map new claims back to original claims ---
            # Create a quick lookup for the original claim data
            original_claim_lookup = {c['claim_id']: c for c in claims_for_doc}

            # 5. Format the new claim(s)
            for new_claim_data in new_claims_list:
                original_claim_id = new_claim_data.get("original_claim_id")
                original_claim = original_claim_lookup.get(original_claim_id)

                if not original_claim:
                    logger.warning(f"DRA: AI returned a claim for an unknown original_claim_id '{original_claim_id}'. Skipping.")
                    continue

                # Get canonical sub-requirement
                sub_req = original_claim.get('sub_requirement', 'N/A')

                # Create a new claim ID
                new_claim_hash = hashlib.md5(
                    f"{filename}{sub_req}{new_claim_data['evidence_chunk']}".encode('utf-8')
                ).hexdigest()

                new_claim_obj = {
                    "claim_id": new_claim_hash,
                    "filename": filename,
                    "pillar": original_claim.get('pillar'),
                    "sub_requirement": sub_req,
                    "evidence_chunk": new_claim_data.get('evidence_chunk'),
                    "claim_summary": new_claim_data.get('claim_summary'),
                    "status": "pending_judge_review",  # Back to the Judge
                    "reviewer_confidence": new_claim_data.get('reviewer_confidence', 0.8),
                    "judge_notes": f"Re-submitted by DRA. (Original rejection: {original_claim.get('judge_notes')})",
                    "review_timestamp": datetime.now().isoformat(),
                    "_origin": original_claim.get('_origin')  # Preserve origin (csv_db or json_db)
                }

                if new_claim_obj.get('_origin') == 'csv_db':
                    new_claim_obj['_origin_list'] = original_claim.get('_origin_list')

                new_claims_for_rejudgment.append(new_claim_obj)
                logger.info(f"DRA: Found new, stronger evidence for claim {original_claim_id} in {filename}!")
                safe_print(f"    DRA: Found new evidence for {original_claim_id[:6]}... Re-submitting to Judge.")

        except Exception as e:
            logger.error(f"DRA: Unhandled error during API call for {filename}: {e}")

    logger.info(f"DRA: Deep analysis complete. Returning {len(new_claims_for_rejudgment)} new claims for re-judgment.")
    return new_claims_for_rejudgment