"""
Enhanced Research Gap Analysis Orchestrator
Runs Judge on new data *before* baseline analysis.
Implements iterative deep-review loop, convergence checking, and score history.
Version: 3.6 (Pre-Analysis Judge Run)
"""

import pandas as pd
import json
import os
import sys
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
import ReviewPlotter as plotter
import networkx as nx
import logging
from collections import defaultdict
import pickle
import csv
import hashlib
from sentence_transformers import SentenceTransformer
import subprocess  # To run external scripts
from pathlib import Path  # For file state checking

# --- CONFIGURATION & SETUP ---
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gap_analysis.log', encoding='utf-8'),
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


# --- File Paths ---
# 1. Inputs from other scripts
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'
DEFINITIONS_FILE = 'pillar_definitions_enhanced.json'
# DEPRECATED: DEEP_COVERAGE_DB_FILE = 'deep_coverage_database.json'
# Now using version history as single source of truth (Task Card #4)
VERSION_HISTORY_FILE = 'review_version_history.json'

# 2. This script's state / outputs
OUTPUT_FOLDER = 'gap_analysis_output'
CACHE_FOLDER = 'analysis_cache'
CACHE_FILE = os.path.join(CACHE_FOLDER, 'analysis_cache.pkl')
CONTRIBUTION_REPORT_FILE = os.path.join(OUTPUT_FOLDER, 'sub_requirement_paper_contributions.md')
ORCHESTRATOR_STATE_FILE = 'orchestrator_state.json'
DEEP_REVIEW_DIRECTIONS_FILE = os.path.join(OUTPUT_FOLDER, 'deep_review_directions.json')

# 3. External Scripts to call
DEEP_REVIEWER_SCRIPT = 'Deep-Reviewer.py'
JUDGE_SCRIPT = 'Judge.py'

# Create directories
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Analysis configuration
ANALYSIS_CONFIG = {
    'MIN_PAPERS_FOR_ANALYSIS': 3,
    'QUALITY_WEIGHT_THRESHOLD': 0.7,
    'ENABLE_TREND_ANALYSIS': True,
    'ENABLE_NETWORK_ANALYSIS': True,
    'CACHE_RESULTS': True,
    'EXPORT_FORMATS': ['html', 'json', 'latex'],
    'API_CALLS_PER_MINUTE': 60,
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,
    'CONVERGENCE_THRESHOLD': 5.0  # 5% threshold
}


# --- HELPER CLASSES ---

# --- APIManager Class (Unchanged) ---
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
                temperature=0.2, top_p=1.0, top_k=1, max_output_tokens=16384,
                response_mime_type="application/json", thinking_config=thinking_config
            )
            self.text_generation_config = types.GenerateContentConfig(
                temperature=0.2, top_p=1.0, top_k=1, max_output_tokens=16384,
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
        current_time = time.time()
        if current_time - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = current_time
        if self.calls_this_minute >= ANALYSIS_CONFIG['API_CALLS_PER_MINUTE']:
            sleep_time = 60.1 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.info(f"Rate limit ({ANALYSIS_CONFIG['API_CALLS_PER_MINUTE']}/min) reached. Sleeping for {sleep_time:.1f} seconds...")
                safe_print(f"⏳ Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
                self.calls_this_minute = 0
                self.minute_start = time.time()
        self.calls_this_minute += 1

    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        if use_cache and prompt_hash in self.cache:
            logger.debug(f"Cache hit for hash: {prompt_hash}")
            safe_print("📦 Using cached response")
            return self.cache[prompt_hash]
        logger.debug(f"Cache miss for hash: {prompt_hash}. Calling API...")
        self.rate_limit()
        response_text = ""
        for attempt in range(ANALYSIS_CONFIG['RETRY_ATTEMPTS']):
            try:
                current_config_object = self.json_generation_config if is_json else self.text_generation_config
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt, config=current_config_object
                )
                response_text = response.text
                result = json.loads(response_text) if is_json else response_text
                self.cache[prompt_hash] = result
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}. Response text: '{response_text[:500]}...'")
                if attempt < ANALYSIS_CONFIG['RETRY_ATTEMPTS'] - 1: time.sleep(ANALYSIS_CONFIG['RETRY_DELAY'])
                else: logger.error("Max retries reached for JSON decode error.")
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


# --- ResearchDatabase Class (Unchanged) ---
class ResearchDatabase:
    """Manages the research paper database"""
    def __init__(self, csv_file: str):
        self.db = None
        self.load_database(csv_file)
        self.paper_network = None
        if ANALYSIS_CONFIG['ENABLE_NETWORK_ANALYSIS'] and self.db is not None:
            self.build_network()

    def load_database(self, csv_file: str):
        try:
            self.db = pd.read_csv(csv_file)
            for col in self.db.select_dtypes(include=['object']).columns:
                 self.db[col] = self.db[col].fillna('')
            score_columns = [
                'CORE_DOMAIN_RELEVANCE_SCORE', 'SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE',
                'REPRODUCIBILITY_SCORE', 'BIOLOGICAL_FIDELITY', 'EXTRACTION_QUALITY'
            ]
            for col in score_columns:
                if col in self.db.columns:
                    self.db[col] = pd.to_numeric(self.db[col], errors='coerce').fillna(0)
            if 'PUBLICATION_YEAR' in self.db.columns:
                self.db['PUBLICATION_YEAR'] = pd.to_numeric(self.db['PUBLICATION_YEAR'], errors='coerce')
            self.db.fillna(0, inplace=True)
            if 'FILENAME' in self.db.columns:
                self.db['FILENAME'] = self.db['FILENAME'].astype(str)
            logger.info(f"[SUCCESS] Loaded {len(self.db)} papers from database")
        except FileNotFoundError:
            logger.error(f"[ERROR] Database file not found: {csv_file}")
            self.db = pd.DataFrame()
        except pd.errors.ParserError as e:
            logger.critical(f"[ERROR] FAILED TO PARSE CSV: {e}")
            logger.critical(f"CRITICAL: The file '{csv_file}' is corrupt. Please DELETE or RENAME it before running again.")
            safe_print(f"❌ CRITICAL: The file '{csv_file}' is corrupt. Please DELETE it and re-run.")
            self.db = pd.DataFrame()
        except Exception as e:
            logger.error(f"[ERROR] Error loading database: {e}")
            self.db = pd.DataFrame()

    def build_network(self):
        if self.db is None or self.db.empty: return
        self.paper_network = nx.DiGraph()
        for idx, row in self.db.iterrows():
            if row['FILENAME']:
                self.paper_network.add_node(row['FILENAME'], **row.to_dict())
        col_to_use = None
        if 'MENTIONED_PAPERS' in self.db.columns: col_to_use = 'MENTIONED_PAPERS'
        elif 'CROSS_REFERENCES' in self.db.columns: col_to_use = 'CROSS_REFERENCES'
        if col_to_use:
            logger.info(f"Building network edges from {col_to_use}...")
            edges_added = 0
            for idx, row in self.db.iterrows():
                source_node = row['FILENAME']
                if not source_node: continue
                ref_string = str(row[col_to_use])
                if ref_string.startswith('['):
                    try: targets = json.loads(ref_string.replace("'", "\""))
                    except json.JSONDecodeError: targets = []
                else: targets = ref_string.split(',')
                for target_node in targets:
                    target_node = str(target_node).strip()
                    if self.paper_network.has_node(target_node):
                        self.paper_network.add_edge(source_node, target_node)
                        edges_added += 1
            logger.info(f"   Added {edges_added} citation edges.")
        else: logger.warning("No 'MENTIONED_PAPERS' or 'CROSS_REFERENCES' column found.")
        logger.info(f"[INFO] Built network with {self.paper_network.number_of_nodes()} nodes")

    def get_relevant_papers(self, pillar_name: str, pillar_keywords: List[str]) -> pd.DataFrame:
        if self.db is None or self.db.empty:
            return pd.DataFrame(columns=self.db.columns)
        pillar_short = pillar_name.split(':')[1].split('(')[0].strip() if ':' in pillar_name else pillar_name
        conditions = []
        search_fields = [
            'CORE_DOMAIN', 'SUB_DOMAIN', 'APPLICABILITY_NOTES',
            'KEYWORDS', 'CORE_CONCEPTS', 'INTERDISCIPLINARY_BRIDGES', 'MAJOR_FINDINGS', 'TITLE'
        ]
        search_terms = [pillar_short] + pillar_keywords
        for field in search_fields:
            if field in self.db.columns:
                for keyword in search_terms:
                    if keyword:
                        condition = self.db[field].str.contains(keyword, case=False, na=False)
                        conditions.append(condition)
        if conditions:
            combined = pd.concat(conditions, axis=1).any(axis=1)
            relevant = self.db[combined].drop_duplicates(subset=['FILENAME'])
        else:
            relevant = pd.DataFrame(columns=self.db.columns)
        return relevant

    def calculate_paper_quality(self, paper: pd.Series) -> float:
        quality_factors = {
            'REPRODUCIBILITY_SCORE': 0.2, 'BIOLOGICAL_FIDELITY': 0.15,
            'CORE_DOMAIN_RELEVANCE_SCORE': 0.25, 'SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE': 0.25,
            'EXTRACTION_QUALITY': 0.15
        }
        total_score, total_weight = 0, 0
        for factor, weight in quality_factors.items():
            if factor in paper and pd.notna(paper[factor]):
                try:
                    value = float(paper[factor])
                    total_score += value * weight
                    total_weight += weight
                except (ValueError, TypeError): continue
        if total_weight > 0: return (total_score / total_weight)
        return 50.0

    def get_key_papers(self, n: int = 10) -> pd.DataFrame:
        if 'quality_score' not in self.db.columns:
            self.db['quality_score'] = self.db.apply(self.calculate_paper_quality, axis=1)
        if self.paper_network is None or self.paper_network.number_of_nodes() == 0:
            logger.warning("Network not built. Falling back to quality score.")
            return self.db.nlargest(n, 'quality_score')
        try:
            centrality = nx.pagerank(self.paper_network, alpha=0.85)
            self.db['centrality'] = self.db['FILENAME'].map(centrality).fillna(0)
            self.db['importance'] = (0.6 * self.db['centrality'] * 1000 + 0.4 * self.db['quality_score'])
            return self.db.nlargest(n, 'importance')
        except Exception as e:
            logger.warning(f"Centrality calculation failed: {e}. Falling back to quality score.")
            return self.db.nlargest(n, 'quality_score')
# --- END ResearchDatabase Class ---


# --- PillarAnalyzer Class (MODIFIED) ---
class PillarAnalyzer:
    """Analyzes research completeness for each pillar"""

    # --- MODIFIED: Now takes parsed CSV data and approved deep claims ---
    def __init__(self, definitions: Dict, database: ResearchDatabase,
                 api_manager: APIManager, all_db_records: List[Dict],
                 approved_deep_claims: List[Dict]):
        self.definitions = definitions
        self.database = database # The ResearchDatabase object
        self.all_db_records = all_db_records # The raw list of dicts from CSV
        self.api_manager = api_manager
        self.approved_deep_claims = approved_deep_claims # Approved claims from JSON DB
        self.cache = {}
        self.load_cache()

    def load_cache(self):
        if os.path.exists(CACHE_FILE) and ANALYSIS_CONFIG['CACHE_RESULTS']:
            try:
                with open(CACHE_FILE, 'rb') as f: self.cache = pickle.load(f)
                logger.info(f"[INFO] Loaded {len(self.cache)} cached analyses from {CACHE_FILE}")
            except Exception as e:
                logger.warning(f"Could not load cache: {e}. Deleting old cache.")
                if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE)
                self.cache = {}

    def save_cache(self):
        if not ANALYSIS_CONFIG['CACHE_RESULTS']: return
        try:
            with open(CACHE_FILE, 'wb') as f: pickle.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")

    # --- MODIFIED: build_expert_prompt (to include ALL approved claims) ---
    def build_expert_prompt(self, pillar_name: str, pillar_data: Dict,
                             relevant_papers: pd.DataFrame) -> Optional[str]:
        """Build comprehensive analysis prompt"""

        # 1. Get High-Level Paper Summaries (from relevant_papers DataFrame)
        papers_to_use = pd.DataFrame()
        if not relevant_papers.empty:
            if 'quality_score' not in relevant_papers.columns:
                relevant_papers['quality_score'] = relevant_papers.apply(
                    self.database.calculate_paper_quality, axis=1
                )
            high_quality = relevant_papers[relevant_papers['quality_score'] >= ANALYSIS_CONFIG['QUALITY_WEIGHT_THRESHOLD'] * 100]
            papers_to_use = high_quality if len(high_quality) >= ANALYSIS_CONFIG['MIN_PAPERS_FOR_ANALYSIS'] else relevant_papers
            logger.info(f"   Using {len(papers_to_use)} high-quality papers for analysis")

        paper_summaries = []
        for _, row in papers_to_use.iterrows():
            summary = f"""
---
(Source: Paper Summary)
PAPER: {row.get('TITLE', 'N/A')} 
FILENAME: {row.get('FILENAME', 'N/A')}
FINDINGS: {row.get('MAJOR_FINDINGS', 'N/A')}
CORE_CONCEPTS: {row.get('CORE_CONCEPTS', 'N/A')}
---
"""
            paper_summaries.append(summary)

        # 2. Get Approved Claims from Deep Coverage DB (JSON file)
        claims_from_json_db = [
            c for c in self.approved_deep_claims
            if c.get('pillar') == pillar_name
        ]

        # 3. Get Approved Claims from Research DB (CSV file)
        claims_from_csv_db = []
        for row in self.all_db_records:
            for claim in row.get("Requirement(s)", []):
                if claim.get('pillar') == pillar_name and claim.get('status') == 'approved':
                    # Add context for the AI
                    claim['_filename'] = row.get('FILENAME', 'N/A')
                    claims_from_csv_db.append(claim)

        all_approved_claims = claims_from_json_db + claims_from_csv_db

        deep_claims_summaries = []
        if all_approved_claims:
            logger.info(f"   Injecting {len(all_approved_claims)} approved claims (from CSV & JSON).")
            for c in all_approved_claims:
                sub_req_key = c.get('sub_requirement') or c.get('sub_requirement_key', 'N/A')
                claim_str = f"""
---
(Source: Approved Claim)
CLAIM FOR SUB-REQ: {sub_req_key}
FROM PAPER: {c.get('filename') or c.get('_filename', 'N/A')}
EVIDENCE CHUNK: {c.get('evidence_chunk', 'N/A')}
REVIEWER'S CLAIM: {c.get('claim_summary', 'N/A')}
JUDGE'S RULING: {c.get('judge_notes', 'Approved.')}
---
"""
                deep_claims_summaries.append(claim_str)

        if papers_to_use.empty and not all_approved_claims:
            return None # Nothing to analyze

        metrics_str = ""
        if 'quantitative_metrics' in pillar_data:
            metrics_str = f"QUANTITATIVE TARGETS:\n{json.dumps(pillar_data['quantitative_metrics'], indent=2)}\n"

        return f"""
You are an expert research gap analyst. Your task is to evaluate a body of literature against detailed research requirements.

--- PILLAR & REQUIREMENTS ---
PILLAR: "{pillar_name}"
DESCRIPTION: {pillar_data.get('description', '')}
{metrics_str}
REQUIREMENTS TO EVALUATE:
{json.dumps(pillar_data['requirements'], indent=2)}

--- EVIDENCE: 1. HIGH-LEVEL LITERATURE ({len(papers_to_use)} papers) ---
{"".join(paper_summaries) if paper_summaries else "No high-level papers found."}

--- EVIDENCE: 2. APPROVED JUDGED CLAIMS ({len(all_approved_claims)} claims) ---
{"".join(deep_claims_summaries) if deep_claims_summaries else "No approved claims found."}

--- INSTRUCTIONS ---
1.  Analyze how the provided evidence addresses each requirement and sub-requirement.
2.  You MUST use BOTH the "HIGH-LEVEL LITERATURE" (summaries) AND the "APPROVED JUDGED CLAIMS" (specific, judged chunks) to form your assessment.
3.  The Approved Claims are granular and judged to be true; give them significant weight for the specific sub-requirement they target.
4.  For each sub-requirement, provide:
    - completeness_percent (0-100): Your estimate of how completely the requirement is addressed by the *entire* body of evidence provided.
    - gap_analysis: What specific aspects are still missing.
    - confidence_level: Your confidence in the assessment (low/medium/high).
    - contributing_papers: A list of JSON objects. For each paper OR claim that *significantly* contributes, add an object with:
        - "filename": The FILENAME of the paper.
        - "contribution_summary": A 1-sentence explanation of *what* this paper/claim contributes.
        - "estimated_contribution_percent": Your estimate (0-100) of how much this *single paper/claim* contributes.

SCORING GUIDELINES (for 'completeness_percent'):
- 0-20%: Topic barely mentioned
- 21-40%: Basic theoretical discussion
- 41-60%: Partial implementation or proof-of-concept 
- 61-80%: Solid implementation with some limitations
- 81-99%: Near-complete solution with minor gaps
- 100%: Requirement fully satisfied with robust validation

Return ONLY a JSON object with the exact structure:
{{
  "requirement_key": {{
    "sub_requirement_key": {{ ... }}
  }}
}}
"""
    # --- END MODIFICATION ---

    def analyze_pillar(self, pillar_name: str, pillar_data: Dict) -> Tuple[Dict, float, List]:
        """Analyze a single pillar's completeness."""
        # --- MODIFIED: Cache key now includes all data sources ---
        cache_key = f"{pillar_name}_{len(self.database.db)}_{len(self.all_db_records)}_{len(self.approved_deep_claims)}"

        if cache_key in self.cache:
            logger.info(f"   Found cached analysis for {pillar_name} (key: {cache_key})")
            return self.cache[cache_key]

        keywords = pillar_data.get('keywords', [])
        relevant_papers_df = self.database.get_relevant_papers(pillar_name, keywords)
        logger.info(f"   Found {len(relevant_papers_df)} relevant papers from main DB.")

        # Check if we have *any* data for this pillar
        has_csv_claims = any(
            claim.get('pillar') == pillar_name
            for row in self.all_db_records
            for claim in row.get("Requirement(s)", [])
        )
        has_json_claims = any(c.get('pillar') == pillar_name for c in self.approved_deep_claims)

        if relevant_papers_df.empty and not has_csv_claims and not has_json_claims:
            logger.warning(f"   No relevant papers or claims for meaningful analysis.")
            empty_results = self._create_empty_results(pillar_data['requirements'])
            completeness, waterfall = self._calculate_weighted_completeness(
                pillar_data['requirements'], empty_results, pd.DataFrame()
            )
            return empty_results, completeness, waterfall

        prompt = self.build_expert_prompt(pillar_name, pillar_data, relevant_papers_df)
        if not prompt:
            empty_results = self._create_empty_results(pillar_data['requirements'])
            completeness, waterfall = self._calculate_weighted_completeness(
                pillar_data['requirements'], empty_results, pd.DataFrame()
            )
            return empty_results, completeness, waterfall

        try:
            logger.info(f"   Sending analysis prompt ({len(prompt)} chars) to Gemini...")
            analysis_results = self.api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
            if not analysis_results:
                raise Exception("API call returned None")

            analysis_results = self._validate_results(analysis_results, pillar_data['requirements'])
            completeness, waterfall = self._calculate_weighted_completeness(
                pillar_data['requirements'],
                analysis_results,
                relevant_papers_df # Pass the DF for quality scoring
            )
            self.cache[cache_key] = (analysis_results, completeness, waterfall)
            self.save_cache()
            return analysis_results, completeness, waterfall

        except Exception as e:
            logger.error(f"   Error in pillar analysis: {e}")
            empty_results = self._create_empty_results(pillar_data['requirements'])
            completeness, waterfall = self._calculate_weighted_completeness(
                pillar_data['requirements'], empty_results, pd.DataFrame()
            )
            return empty_results, completeness, waterfall

    # --- Unmodified private methods: _create_empty_results, _validate_results, _calculate_weighted_completeness ---
    def _create_empty_results(self, requirements: Dict) -> Dict:
        results = {}
        for req_key, sub_reqs in requirements.items():
            results[req_key] = {}
            for sub_req in sub_reqs:
                results[req_key][sub_req] = {
                    "completeness_percent": 0,
                    "gap_analysis": "No relevant papers or claims found",
                    "confidence_level": "low",
                    "contributing_papers": []
                }
        return results

    def _validate_results(self, results: Dict, requirements: Dict) -> Dict:
        validated = {}
        for req_key, sub_reqs in requirements.items():
            validated[req_key] = {}
            for sub_req in sub_reqs:
                default_sub_req = {
                    "completeness_percent": 0, "gap_analysis": "Error parsing AI response",
                    "confidence_level": "low", "contributing_papers": []
                }
                try:
                    sub_req_data = results.get(req_key, {}).get(sub_req, default_sub_req)
                    contrib_papers = sub_req_data.get("contributing_papers", [])
                    if not isinstance(contrib_papers, list):
                        logger.warning(f"Sanitizing 'contributing_papers' for {sub_req}: was not a list.")
                        contrib_papers = []
                    valid_papers = []
                    for item in contrib_papers:
                        if isinstance(item, dict) and 'filename' in item and 'contribution_summary' in item and 'estimated_contribution_percent' in item:
                            valid_papers.append(item)
                        else:
                            logger.warning(f"Skipping invalid item in 'contributing_papers' for {sub_req}: {item}")
                    sub_req_data["contributing_papers"] = valid_papers
                    validated[req_key][sub_req] = sub_req_data
                except Exception:
                    validated[req_key][sub_req] = default_sub_req
        return validated

    def _calculate_weighted_completeness(self, requirements_def: Dict,
                                         analysis_results: Dict,
                                         papers_df: pd.DataFrame) -> Tuple[float, List]:
        waterfall_steps, requirement_scores = [], []
        if 'quality_score' not in papers_df.columns and not papers_df.empty:
            papers_df['quality_score'] = papers_df.apply(self.database.calculate_paper_quality, axis=1)

        for main_req, sub_reqs in requirements_def.items():
            sub_scores, sub_gaps = [], []
            if main_req in analysis_results:
                for sub_req in sub_reqs:
                    if sub_req in analysis_results[main_req]:
                        result = analysis_results[main_req][sub_req]
                        score = result.get("completeness_percent", 0)
                        confidence = result.get("confidence_level", "medium")
                        confidence_weights = {"high": 1.0, "medium": 0.9, "low": 0.7}
                        score *= confidence_weights.get(confidence, 0.9)

                        evidence_papers = [p.get("filename") for p in result.get("contributing_papers", []) if p.get("filename")]
                        if evidence_papers and not papers_df.empty:
                            paper_qualities = []
                            for filename in evidence_papers:
                                paper = papers_df[papers_df['FILENAME'] == filename] # Use the passed DF
                                if not paper.empty:
                                    quality = paper.iloc[0].get('quality_score', 50)
                                    paper_qualities.append(quality / 100)
                            if paper_qualities:
                                avg_quality = np.mean(paper_qualities)
                                score *= (0.7 + 0.3 * avg_quality)
                        sub_scores.append(score)
                        if score < 100:
                            gap_text = result.get("gap_analysis", "No details")
                            confidence_text = f"[{confidence} confidence]"
                            sub_gaps.append(f"  - {sub_req.split(':')[0]} ({score:.0f}%): {gap_text} {confidence_text}")
                    else:
                        sub_scores.append(0)
                        sub_gaps.append(f"  - {sub_req.split(':')[0]} (0%): Not defined in analysis")
            else:
                sub_scores = [0] * len(sub_reqs)
                sub_gaps = [f"  - (0%): Main requirement not analyzed"]
            main_req_avg = np.mean(sub_scores) if sub_scores else 0
            requirement_scores.append(main_req_avg)
            waterfall_steps.append({
                "requirement": main_req.split(':')[0], "value": round(main_req_avg, 1),
                "gap_analysis": "\n".join(sub_gaps) if sub_gaps else "Complete"
            })
        total_completeness = np.mean(requirement_scores) if requirement_scores else 0
        return total_completeness, waterfall_steps
# --- END PillarAnalyzer Class ---


# --- TrendAnalyzer Class (Unchanged) ---
class TrendAnalyzer:
    """Analyze research trends over time"""
    def __init__(self, database: ResearchDatabase):
        self.database = database
        self.trends = {}
    def analyze_trends(self, pillar_definitions: Dict) -> Dict:
        if self.database.db is None or 'PUBLICATION_YEAR' not in self.database.db.columns:
            logger.warning("No publication year data for trend analysis")
            return {}
        valid_years = self.database.db['PUBLICATION_YEAR'].dropna()
        if valid_years.empty:
            logger.warning("No valid publication year data found for trend analysis.")
            return {}
        min_year, max_year = int(valid_years.min()), int(datetime.now().year)
        if min_year > max_year:
            logger.warning("Min publication year is in the future.")
            return {}
        trends = {}
        valid_db = self.database.db[pd.notna(self.database.db['PUBLICATION_YEAR'])]
        all_papers_by_year = valid_db.groupby('PUBLICATION_YEAR').size()
        for year in range(min_year, max_year + 1):
            year_total_papers = all_papers_by_year.get(year, 0)
            year_coverage = {}
            for pillar_name in pillar_definitions.keys():
                keywords = pillar_definitions[pillar_name].get('keywords', [])
                relevant_papers = self.database.get_relevant_papers(pillar_name, keywords)
                relevant_year = relevant_papers[relevant_papers['PUBLICATION_YEAR'] == year]
                absolute_count = len(relevant_year)
                relative_focus = (absolute_count / max(year_total_papers, 1)) * 100
                year_coverage[pillar_name] = {"absolute_count": absolute_count, "relative_focus_percent": relative_focus}
            trends[year] = year_coverage
        self.trends = trends
        return trends
    def get_velocity(self, pillar_name: str, metric_type: str = 'absolute_count') -> float:
        if not self.trends: return 0.0
        years = sorted(self.trends.keys())
        if len(years) < 3: return 0.0
        recent_years = years[-5:]
        values = [self.trends[year].get(pillar_name, {}).get(metric_type, 0) for year in recent_years]
        if not values: return 0.0
        x, y = np.arange(len(values)), np.array(values)
        try:
            m, c = np.polyfit(x, y, 1)
            return m
        except np.linalg.LinAlgError: return 0.0
# --- END TrendAnalyzer Class ---


# --- ReportGenerator Class (Unchanged) ---
class ReportGenerator:
    """Generate comprehensive reports in multiple formats"""
    def __init__(self, output_folder: str):
        self.output_folder = output_folder
    def generate_latex_report(self, results: Dict, filename: str = "gap_analysis_report.tex"):
        pass # Code omitted for brevity
    def generate_json_report(self, results: Dict, filename: str = "gap_analysis_report.json"):
        filepath = os.path.join(self.output_folder, filename)
        try:
            with open(filepath, 'w') as f: json.dump(results, f, indent=2, default=str)
            logger.info(f"JSON report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to write JSON report: {e}")
    def generate_contribution_report_md(self, all_results: Dict, filename: str = CONTRIBUTION_REPORT_FILE):
        logger.info(f"Generating paper contribution report to {filename}...")
        report_content = [f"# Paper Contribution Stack-up Report\n_Generated: {datetime.now().isoformat()}_\n"]
        for pillar_name, pillar_data in all_results.items():
            report_content.append(f"\n## Pillar: {pillar_name.split(':')[-1].strip()}")
            report_content.append(f"**Overall Completeness: {pillar_data['completeness']:.1f}%**\n")
            for req_key, req_data in pillar_data.get('analysis', {}).items():
                report_content.append(f"### Requirement: {req_key.split(':')[-1].strip()}")
                for sub_req_key, sub_req_data in req_data.items():
                    report_content.append(f"\n####  Sub-Requirement: {sub_req_key.split(':')[-1].strip()}")
                    report_content.append(f"- **Completeness:** {sub_req_data.get('completeness_percent', 0):.1f}%")
                    report_content.append(f"- **Gap Analysis:** {sub_req_data.get('gap_analysis', 'N/A')}")
                    report_content.append(f"- **Confidence:** {sub_req_data.get('confidence_level', 'N/A')}")
                    contributions = sub_req_data.get('contributing_papers', [])
                    if contributions:
                        report_content.append(f"- **Contributing Papers ({len(contributions)}):**")
                        report_content.append("| Paper | Est. Contribution % | Justification |")
                        report_content.append("| :--- | :--- | :--- |")
                        for paper in sorted(contributions, key=lambda x: x.get('estimated_contribution_percent', 0), reverse=True):
                            report_content.append(f"| {paper.get('filename', 'N/A')} | {paper.get('estimated_contribution_percent', 0)}% | {paper.get('contribution_summary', 'N/A')} |")
                    else:
                        report_content.append("- **Contributing Papers:** None")
        try:
            with open(filename, 'w', encoding='utf-8') as f: f.write("\n".join(report_content))
            logger.info(f"Successfully saved contribution report to {filename}")
        except Exception as e:
            logger.error(f"Failed to write contribution report: {e}")
# --- END ReportGenerator Class ---


# --- PRE-MAIN HELPER FUNCTIONS (Unchanged) ---
def extract_key_gaps(analysis: Dict) -> List[str]:
    gaps = []
    for req, sub_reqs in analysis.items():
        for sub_req, result in sub_reqs.items():
            completeness = result.get('completeness_percent', 0)
            if 0 < completeness < 50:
                gap_text = f"{sub_req.split(':')[0]}: {result.get('gap_analysis', 'No details')}"
                gaps.append((completeness, gap_text))
    gaps.sort(key=lambda x: x[0])
    return [g[1] for g in gaps[:3]]

def identify_critical_gaps(results: Dict) -> List[str]:
    critical_gaps = []
    for pillar_name, pillar_result in results.items():
        if pillar_result['completeness'] < 30:
            critical_gaps.append((pillar_result['completeness'], f"{pillar_name.split(':')[0]}: Critically low completeness ({pillar_result['completeness']:.1f}%)"))
        for req, sub_reqs in pillar_result.get('analysis', {}).items():
            for sub_req, result in sub_reqs.items():
                if result.get('completeness_percent', 0) == 0:
                    critical_gaps.append((-1, f"{pillar_name.split(':')[0]} - {sub_req.split(':')[0]}: Completely unaddressed"))
    critical_gaps.sort(key=lambda x: x[0])
    return [g[1] for g in critical_gaps[:10]]

def generate_recommendations(results: Dict, database: ResearchDatabase) -> List[Dict]:
    return [] # Code omitted for brevity

def generate_executive_summary(results: Dict, database: ResearchDatabase, output_folder: str):
    pass # Code omitted for brevity
# --- END PRE-MAIN HELPER FUNCTIONS ---


# --- STATE & ITERATION FUNCTIONS (MODIFIED) ---

def load_orchestrator_state(state_file: str) -> Tuple[Dict, Dict, Dict]:
    """Loads the orchestrator's last run state, results, and score history."""
    if not os.path.exists(state_file):
        logger.info("No orchestrator state file found. Starting fresh.")
        return {"file_states": {}}, {}, {"iteration_timestamps": [], "sub_req_scores": {}}

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
            last_run_state = state.get("last_run_state", {"file_states": {}})
            previous_results = state.get("previous_results", {})
            score_history = state.get("score_history", {"iteration_timestamps": [], "sub_req_scores": {}})
            logger.info("Successfully loaded previous orchestrator state.")
            return last_run_state, previous_results, score_history
    except Exception as e:
        logger.warning(f"Error loading state file: {e}. Starting fresh.")
        return {"file_states": {}}, {}, {"iteration_timestamps": [], "sub_req_scores": {}}

def save_orchestrator_state(state_file: str, previous_results: Dict, score_history: Dict):
    """Saves the current run state, results, and score history."""
    state = {
        "last_run_timestamp": datetime.now().isoformat(),
        "last_run_state": {
            "file_states": {
                RESEARCH_DB_FILE: Path(RESEARCH_DB_FILE).stat().st_mtime if os.path.exists(RESEARCH_DB_FILE) else 0,
                VERSION_HISTORY_FILE: Path(VERSION_HISTORY_FILE).stat().st_mtime if os.path.exists(VERSION_HISTORY_FILE) else 0,
            }
        },
        "previous_results": previous_results,
        "score_history": score_history
    }
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Successfully saved orchestrator state to {state_file}")
    except Exception as e:
        logger.error(f"Error saving orchestrator state: {e}")

def check_for_new_data(last_run_state: Dict) -> bool:
    """Checks if input files have been modified since the last run."""
    last_states = last_run_state.get("file_states", {})

    # Check Journal Reviewer DB
    last_db_mtime = last_states.get(RESEARCH_DB_FILE, 0)
    current_db_mtime = Path(RESEARCH_DB_FILE).stat().st_mtime if os.path.exists(RESEARCH_DB_FILE) else 0
    if current_db_mtime > last_db_mtime:
        logger.info(f"New data detected in {RESEARCH_DB_FILE}.")
        return True

    # Check Version History
    last_version_mtime = last_states.get(VERSION_HISTORY_FILE, 0)
    current_version_mtime = Path(VERSION_HISTORY_FILE).stat().st_mtime if os.path.exists(VERSION_HISTORY_FILE) else 0
    if current_version_mtime > last_version_mtime:
        logger.info(f"New data detected in {VERSION_HISTORY_FILE}.")
        return True

    logger.info("No new file data detected since last run.")
    return False

def get_user_analysis_target(pillar_definitions: Dict) -> Tuple[List[str], str]:
    """Asks the user what to analyze. Returns (pillar_list, run_mode)."""
    safe_print("\n--- No new data detected ---")
    safe_print("What would you like to re-assess?")

    pillar_names = list(pillar_definitions.keys())
    for i, name in enumerate(pillar_names, 1):
        safe_print(f"  {i}. {name.split(':')[0]}")
    safe_print("\n  ALL - Run analysis on all pillars (one pass)")
    safe_print("  DEEP - Run iterative deep-review loop on all pillars")
    safe_print("  NONE - Exit (default)")

    choice = input("Enter choice (1-6, ALL, DEEP, NONE): ").strip().upper()

    if not choice or choice == "NONE":
        return [], "EXIT"
    if choice == "ALL":
        return pillar_names, "ONCE"
    if choice == "DEEP":
        return pillar_names, "DEEP_LOOP"
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(pillar_names):
            return [pillar_names[choice_idx]], "ONCE"
    except ValueError:
        pass

    safe_print("Invalid choice. Exiting.")
    return [], "EXIT"


def run_script(script_name: str) -> bool:
    """
    Runs an external python script, streaming its stdout/stderr to
    both the terminal (safe_print) and the logger (logger.info) in real-time.
    """
    logger.info(f"--- Executing {script_name} ---")
    safe_print(f"--- 🚀 Executing {script_name} ---")

    # Use Popen to have real-time control over stdout/stderr
    try:
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            encoding='utf-8',
            errors='replace',  # Handle potential encoding errors gracefully
            bufsize=1  # Line-buffered
        )

        # Read output line-by-line as it's generated
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                line = line.strip()
                safe_print(f"  [{script_name}] {line}")  # Print to terminal
                logger.info(line)  # Log to file

        # Wait for the process to complete and get the return code
        process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, " ".join(process.args))

        logger.info(f"--- {script_name} finished successfully (Return Code: {process.returncode}) ---")
        safe_print(f"--- ✅ {script_name} finished successfully ---")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"CRITICAL: {script_name} failed with exit code {e.returncode}")
        logger.error(f"The error message from {script_name} should be visible above.")
        safe_print(f"--- ❌ CRITICAL: {script_name} failed. See log. ---")
        return False
    except FileNotFoundError:
        logger.error(f"CRITICAL: Script not found: {script_name}")
        safe_print(f"--- ❌ CRITICAL: Script not found: {script_name} ---")
        return False
    except Exception as e:
        logger.error(f"An unhandled error occurred while running {script_name}: {e}")
        safe_print(f"--- ❌ CRITICAL: An error occurred with {script_name}. See log. ---")
        return False

# --- MODIFIED: Load functions now parse data for PillarAnalyzer ---
def load_research_db_records(filepath: str) -> List[Dict]:
    """Loads the research CSV and parses JSON in 'Requirement(s)' column."""
    if not os.path.exists(filepath):
        logger.error(f"Research DB file not found: {filepath}.")
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
                    row["Requirement(s)"] = []
            elif not isinstance(req_data, list):
                row["Requirement(s)"] = []
            parsed_records.append(row)
        logger.info(f"Loaded and parsed {len(parsed_records)} records from {filepath}")
        return parsed_records
    except Exception as e:
        logger.error(f"Could not load or parse research DB {filepath}: {e}")
        return []

def load_approved_claims_from_version_history(filepath: str) -> List[Dict]:
    """Loads the version history and filters for 'approved' claims."""
    if not os.path.exists(filepath):
        logger.info("No version history file found.")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            version_history = json.load(f)
        
        # Extract all claims from version history
        all_claims = []
        for filename, versions in version_history.items():
            if not versions:
                continue
            # Get latest version
            latest_version = versions[-1]
            review = latest_version.get('review', {})
            requirements_list = review.get('Requirement(s)', [])
            
            for claim in requirements_list:
                # Add filename for context
                claim_with_file = claim.copy()
                claim_with_file['filename'] = filename
                all_claims.append(claim_with_file)
        
        approved_claims = [c for c in all_claims if c.get("status") == "approved"]
        logger.info(f"Loaded {len(all_claims)} total claims, {len(approved_claims)} are 'approved'.")
        return approved_claims
    except Exception as e:
        logger.error(f"Error loading version history: {e}")
        return []

def write_deep_review_directions(filepath: str, directions: Dict):
    """Writes the sub-requirements that need a deep review."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(directions, f, indent=2)
        logger.info(f"Wrote {len(directions)} sub-requirements to {filepath}")
        if directions:
            safe_print(f"📝 Wrote {len(directions)} new directions for Deep Reviewer.")
        else:
            logger.info("Wrote empty directions file (to trigger 'review all gaps').")
    except Exception as e:
        logger.error(f"Error writing directions file: {e}")

def get_sub_req_score(result_data: Dict, pillar: str, req: str, sub_req: str) -> float:
    """Safely get a sub-requirement score from a results dictionary."""
    try:
        return result_data[pillar]['analysis'][req][sub_req]['completeness_percent']
    except KeyError:
        return 0.0

def compare_scores(
    previous_results: Dict,
    current_results: Dict,
    definitions: Dict,
    threshold: float
) -> Tuple[bool, Dict, Dict]:
    """
    Compares current vs. previous scores.
    Returns: (needs_new_loop, directions_dict, score_diffs_dict)
    """
    needs_new_loop, directions, score_diffs = False, {}, {}

    if not previous_results:
        logger.info("No previous scores to compare. Assuming first run.")
        # We need to generate directions for ALL gaps < 100%
        threshold = -101 # Ensure any change (even 0) is "above" threshold

    for pillar_name, pillar_data in definitions.items():
        for req_key, sub_req_list in pillar_data.get('requirements', {}).items():
            for sub_req_key in sub_req_list:
                prev_score = get_sub_req_score(previous_results, pillar_name, req_key, sub_req_key)
                curr_score = get_sub_req_score(current_results, pillar_name, req_key, sub_req_key)
                delta = curr_score - prev_score

                if delta > 0:
                    score_diffs[sub_req_key] = {"prev": prev_score, "curr": curr_score, "delta": delta}

                if delta > threshold and curr_score < 100:
                    needs_new_loop = True
                    directions[sub_req_key] = {
                        "pillar": pillar_name,
                        "requirement_key": req_key
                    }

    return needs_new_loop, directions, score_diffs

def update_score_history(score_history: Dict, current_results: Dict, definitions: Dict) -> Dict:
    """Appends the current scores to the history log for plotting."""
    score_history["iteration_timestamps"].append(datetime.now().isoformat())

    for pillar_name, pillar_data in definitions.items():
        for req_key, sub_req_list in pillar_data.get('requirements', {}).items():
            for sub_req_key in sub_req_list:
                score = get_sub_req_score(current_results, pillar_name, req_key, sub_req_key)
                if sub_req_key not in score_history["sub_req_scores"]:
                    score_history["sub_req_scores"][sub_req_key] = []
                # Add score, but also ensure history is equal length
                history_len = len(score_history["iteration_timestamps"])
                current_len = len(score_history["sub_req_scores"][sub_req_key])
                if history_len > current_len + 1:
                    # Pad with previous score if this sub_req wasn't analyzed
                    last_score = score_history["sub_req_scores"][sub_req_key][-1] if current_len > 0 else 0
                    padding = [last_score] * (history_len - current_len - 1)
                    score_history["sub_req_scores"][sub_req_key].extend(padding)

                score_history["sub_req_scores"][sub_req_key].append(score)

    # Ensure all lists have the same length
    history_len = len(score_history["iteration_timestamps"])
    for sub_req_key in score_history["sub_req_scores"]:
        current_len = len(score_history["sub_req_scores"][sub_req_key])
        if current_len < history_len:
            last_score = score_history["sub_req_scores"][sub_req_key][-1] if current_len > 0 else 0
            padding = [last_score] * (history_len - current_len)
            score_history["sub_req_scores"][sub_req_key].extend(padding)

    return score_history
# --- END NEW FUNCTIONS ---


# --- MAIN EXECUTION (MODIFIED) ---
def main():
    logger.info("\n" + "=" * 80)
    logger.info("ENHANCED GAP ANALYSIS ORCHESTRATOR v3.6 (Pre-Analysis Judge Run)")
    logger.info("=" * 80)
    global_start_time = time.time()

    # --- 1. Load Static Definitions & State ---
    try:
        with open(DEFINITIONS_FILE, 'r') as f:
            definitions = json.load(f)
        logger.info(f"[SUCCESS] Loaded {len(definitions)} pillar definitions")
    except FileNotFoundError:
        logger.error(f"[ERROR] Definitions file not found: {DEFINITIONS_FILE}. Exiting.")
        safe_print(f"❌ Definitions file not found: {DEFINITIONS_FILE}. Exiting.")
        return
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Error decoding JSON from {DEFINITIONS_FILE}. Exiting.")
        safe_print(f"❌ Error decoding JSON from {DEFINITIONS_FILE}. Exiting.")
        return

    last_run_state, previous_results, score_history = load_orchestrator_state(ORCHESTRATOR_STATE_FILE)

    # --- 2. Determine Run Mode & Run Initial Judge ---
    has_new_data = check_for_new_data(last_run_state)
    analysis_target_pillars = []
    run_mode = "" # "ONCE" or "DEEP_LOOP" or "EXIT"
    run_initial_judge = False

    if has_new_data:
        safe_print("📬 New data detected in CSV or JSON. Running Judge to validate claims before analysis.")
        run_initial_judge = True
        analysis_target_pillars = list(definitions.keys())
        run_mode = "DEEP_LOOP"
    else:
        analysis_target_pillars, run_mode = get_user_analysis_target(definitions)
        if run_mode == "EXIT":
            safe_print("Exiting.")
            return
        elif run_mode == "DEEP_LOOP":
            safe_print("🚀 Kicking off user-requested DEEP loop. Generating new claims...")
            # Write empty directions to signal "review all gaps < 100%"
            write_deep_review_directions(DEEP_REVIEW_DIRECTIONS_FILE, {})
            if not run_script(DEEP_REVIEWER_SCRIPT):
                safe_print("❌ Deep Reviewer failed. Halting.")
                return
            run_initial_judge = True # We now have new claims to judge
        elif run_mode == "ONCE":
            safe_print(f"Running single-pass analysis on {len(analysis_target_pillars)} pillar(s).")

    # --- NEW: Initial Judge Run ---
    if run_initial_judge:
        if not run_script(JUDGE_SCRIPT):
            logger.critical("Initial Judge run failed. Halting.")
            safe_print("❌ Initial Judge run failed. Halting.")
            return
        safe_print("✅ Initial data validated by Judge.")
    # --- END NEW BLOCK ---

    # --- 3. Initialize Components ---
    logger.info("\n" + "=" * 80)
    logger.info("INITIALIZING ANALYSIS COMPONENTS")
    try:
        api_manager = APIManager()
        report_generator = ReportGenerator(OUTPUT_FOLDER)
        trend_analyzer = None
    except Exception as e:
        logger.critical(f"Failed to initialize core components: {e}")
        safe_print(f"❌ Failed to initialize core components: {e}")
        return

    all_results = previous_results.copy()
    iteration_count = 0

    # --- 4. Start Iterative Analysis Loop ---
    while True:
        iteration_count += 1
        logger.info(f"\n--- Starting Analysis Iteration {iteration_count} ---")
        safe_print(f"\n--- 🔄 Starting Analysis Iteration {iteration_count} ---")

        # --- 4a. Load databases (fresh every loop) ---
        database_df_obj = ResearchDatabase(RESEARCH_DB_FILE)
        if database_df_obj.db is None or database_df_obj.db.empty:
            logger.error("No data in Research DB. Exiting.")
            safe_print("❌ No data in Research DB. Exiting.")
            return

        # Load the *full* parsed CSV records and *approved* claims from version history
        all_db_records = load_research_db_records(RESEARCH_DB_FILE)
        approved_deep_claims = load_approved_claims_from_version_history(VERSION_HISTORY_FILE)

        # Initialize analyzer with fresh data
        analyzer = PillarAnalyzer(
            definitions, database_df_obj, api_manager,
            all_db_records, approved_deep_claims
        )

        if ANALYSIS_CONFIG['ENABLE_TREND_ANALYSIS'] and trend_analyzer is None:
            trend_analyzer = TrendAnalyzer(database_df_obj)
            if trend_analyzer.analyze_trends(definitions):
                logger.info("[INFO] Analyzed trends.")

        current_iteration_results = {}
        radar_data = {}
        velocity_data = {}

        # --- 4b. Run Analysis on Target Pillars ---
        for pillar_name, pillar_data in definitions.items():
            if pillar_name not in analysis_target_pillars:
                if pillar_name in all_results:
                    current_iteration_results[pillar_name] = all_results[pillar_name]
                    radar_data[pillar_name] = all_results[pillar_name].get('completeness', 0)
                continue

            logger.info(f"\n--- Analyzing: {pillar_name} ---")
            safe_print(f"\n--- Analyzing: {pillar_name} ---")

            analysis_results, completeness, waterfall_steps = analyzer.analyze_pillar(pillar_name, pillar_data)
            logger.info(f"   [SUCCESS] Completeness: {completeness:.1f}%")

            current_iteration_results[pillar_name] = {
                'completeness': completeness, 'analysis': analysis_results, 'waterfall_data': waterfall_steps
            }
            radar_data[pillar_name] = round(completeness, 1)

            if trend_analyzer:
                velocity_abs = trend_analyzer.get_velocity(pillar_name, 'absolute_count')
                velocity_focus = trend_analyzer.get_velocity(pillar_name, 'relative_focus_percent')
                current_iteration_results[pillar_name]['research_velocity'] = velocity_abs
                current_iteration_results[pillar_name]['research_focus_change'] = velocity_focus
                velocity_data[pillar_name] = velocity_abs

        all_results = current_iteration_results.copy()

        # --- 4c. Update History & Compare Scores ---
        score_history = update_score_history(score_history, all_results, definitions)
        needs_new_loop, directions, score_diffs = compare_scores(
            previous_results, all_results, definitions, ANALYSIS_CONFIG['CONVERGENCE_THRESHOLD']
        )

        if score_diffs:
            safe_print("\n--- Score Changes This Iteration ---")
            for sub_req, diff in score_diffs.items():
                safe_print(f"  📈 {sub_req.split(':')[0]}: {diff['prev']:.1f}% -> {diff['curr']:.1f}% (+{diff['delta']:.1f}%)")

        # --- 4d. Decide: Loop Again or Exit? ---
        if run_mode == "ONCE":
            safe_print("\nAnalysis complete (single pass mode).")
            break

        if needs_new_loop:
            safe_print("\nConvergence not met. Running new Deep Review loop...")
            write_deep_review_directions(DEEP_REVIEW_DIRECTIONS_FILE, directions)

            if not run_script(DEEP_REVIEWER_SCRIPT):
                safe_print("❌ Deep Reviewer failed. Halting loop.")
                break
            if not run_script(JUDGE_SCRIPT):
                safe_print("❌ Judge failed. Halting loop.")
                break

            previous_results = all_results.copy()
            analysis_target_pillars = list(definitions.keys()) # Ensure all pillars are re-analyzed
        else:
            safe_print("\n✅ Convergence Reached. No sub-requirement changed by > 5%.")
            write_deep_review_directions(DEEP_REVIEW_DIRECTIONS_FILE, {}) # Clear directions
            break

    # --- 5. Post-Loop: Generate Final Reports ---
    logger.info("\n" + "=" * 80)
    logger.info("Analysis loop complete. Generating final reports...")
    safe_print("\n--- 📊 Generating Final Reports ---")

    for pillar_name, pillar_data in all_results.items():
        plotter.create_waterfall_plot(
            pillar_name, pillar_data.get('waterfall_data', []),
            os.path.join(OUTPUT_FOLDER, f"waterfall_{pillar_name.split(':')[0]}.html")
        )
        if pillar_data.get('analysis'):
            for req_key, req_data in pillar_data['analysis'].items():
                for sub_req_key, sub_req_data in req_data.items():
                    contributions = sub_req_data.get('contributing_papers', [])
                    if contributions:
                        plotter.create_sub_requirement_waterfall(
                            sub_req_key, contributions, sub_req_data.get('completeness_percent', 0),
                            os.path.join(OUTPUT_FOLDER, f"sub_waterfall_{sub_req_key.split(':')[0]}.html")
                        )

    if radar_data:
        plotter.create_radar_plot(
            radar_data, os.path.join(OUTPUT_FOLDER, "_OVERALL_Research_Gap_Radar.html"),
            velocity_data=velocity_data if trend_analyzer else None
        )

    if score_history["iteration_timestamps"]:
        logger.info("Generating convergence plots...")
        try:
            plotter.create_convergence_plots(
                score_history, definitions,
                os.path.join(OUTPUT_FOLDER, "_OVERALL_Score_Convergence.html")
            )
            safe_print("  ✅ Convergence plots generated.")
        except AttributeError:
             logger.warning("`plotter.create_convergence_plots` not found. Skipping.")
             safe_print("  ⚠️ `plotter.create_convergence_plots` not found. Skipping convergence graphs.")
        except Exception as e:
             logger.error(f"Failed to create convergence plots: {e}")
             safe_print(f"  ⚠️ Failed to create convergence plots: {e}")

    if 'json' in ANALYSIS_CONFIG['EXPORT_FORMATS']:
        report_generator.generate_json_report(all_results, "gap_analysis_report.json")

    report_generator.generate_contribution_report_md(all_results)

    database_df_obj = ResearchDatabase(RESEARCH_DB_FILE) # Re-load for final summary
    generate_executive_summary(all_results, database_df_obj, OUTPUT_FOLDER)

    # --- 6. Save Final State ---
    save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history)

    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    safe_print("\n" + "=" * 80)
    safe_print("ANALYSIS COMPLETE")
    if radar_data:
        safe_print(f"📊 Average completeness: {np.mean(list(radar_data.values())):.1f}% after {iteration_count} iteration(s).")
    safe_print(f"Total time: {(time.time() - global_start_time):.2f} seconds.")
    safe_print(f"Reports saved to '{OUTPUT_FOLDER}'")


if __name__ == "__main__":
    main()