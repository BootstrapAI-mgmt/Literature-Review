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
}

# --- Logging ---
logger = logging.getLogger(__name__)


def safe_print(message):
    """Print message safely handling Unicode on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(str(message).encode(sys.stdout.encoding or 'utf-8', 'replace').decode(sys.stdout.encoding or 'utf-8'))


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


# --- CORE LOGIC (MODIFIED) ---

def build_dra_prompt(claims_for_document: List[Dict], full_paper_text: str) -> str:
    """
    Builds the prompt for the Deep Requirements Analyzer AI.
    This prompt includes *all* rejected claims for a single document.
    """

    rejection_list_str = ""
    for i, claim in enumerate(claims_for_document, 1):
        rejection_list_str += f"""
--- REJECTED CLAIM #{i} ---
Requirement ("The Law"): "{claim.get('sub_requirement', 'N/A')}"
Judge's Reason: "{claim.get('judge_notes', 'N/A')}"
Original Evidence: "{claim.get('evidence_chunk', 'N/A')}"
(Internal Claim ID: {claim.get('claim_id')})
"""

    return f"""
You are an expert "Deep Requirements Analyzer." Your task is to re-evaluate a list of claims that were rejected by an impartial Judge. You will find *better* evidence for *all* of them from the full text of the single paper provided.

--- LIST OF REJECTED CLAIMS ---
{rejection_list_str}
--- END OF LIST ---

--- YOUR TASK ---
1.  **Analyze Rejections:** For *each* rejected claim, understand *why* the Judge rejected it (e.g., "too weak," "tangential").
2.  **Scan the FULL TEXT:** Read the entire document provided below.
3.  **Find Better Evidence:** For *each* rejected claim, locate one or more sections of text that *directly* and *strongly* satisfy its specific requirement, addressing the Judge's rejection.
4.  **"More is Better":** Be prepared to pull multiple paragraphs from different sections if needed to build a strong, undeniable case. Combine them into a single `evidence_chunk`.
5.  **Self-Correction:** If you cannot find any text with high confidence that *truly* satisfies a requirement and overcomes the rejection, you MUST NOT return an entry for it.

--- Output Format ---
Return ONLY a JSON object with a single key, "new_claims_to_rejudge", which is a list.
For *each* rejected claim you were able to find *new, better* evidence for, return a new claim object in the list.

Example:
{{
  "new_claims_to_rejudge": [
    {{
      "original_claim_id": "(String) The 'Internal Claim ID' of the rejected claim this new evidence is for.",
      "claim_summary": "(String) Your *new* 1-sentence argument for why this *new, larger* evidence is sufficient.",
      "evidence_chunk": "(String) The full, comprehensive text (potentially multiple paragraphs) that you extracted.",
      "reviewer_confidence": 0.95
    }},
    {{
      "original_claim_id": "(String) The 'Internal Claim ID' for the *second* rejected claim.",
      "claim_summary": "(String) This new evidence from the methods section clearly defines the model.",
      "evidence_chunk": "(String) As seen in Figure 4 and the surrounding text, the model architecture consists of...",
      "reviewer_confidence": 0.90
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

        # 2. Build the new prompt (with ALL claims for this doc)
        prompt = build_dra_prompt(claims_for_doc, full_text)

        # 3. Call API (no cache, always re-analyze)
        try:
            ai_response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)

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

            # 4. Format the new claim(s)
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