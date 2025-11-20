"""
Enhanced Research Gap Analysis Orchestrator
Runs Judge on new data *before* baseline analysis.
Implements iterative deep-review loop, convergence checking, and score history.
Version: 3.7 (Task Card #4: Version History Integration)
"""

import pandas as pd
import json
import os
import sys
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
# Use google.genai (new SDK) for Client() interface
from google import genai
from google.genai import types
from dotenv import load_dotenv
from literature_review.utils import plotter
import networkx as nx
import logging
from collections import defaultdict
import pickle
import csv
import hashlib
from sentence_transformers import SentenceTransformer
import subprocess  # To run external scripts
from pathlib import Path  # For file state checking
from literature_review.reviewers import deep_reviewer
from literature_review.analysis import judge
from literature_review.optimization.search_optimizer import generate_search_plan

# Import global rate limiter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.global_rate_limiter import global_limiter, ErrorAction

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
# OUTPUT_FOLDER will be set dynamically by main() function
# Default value here, but can be overridden by environment variable or config
OUTPUT_FOLDER = os.getenv('LITERATURE_REVIEW_OUTPUT_DIR', 'gap_analysis_output')
CACHE_FOLDER = 'analysis_cache'
CACHE_FILE = os.path.join(CACHE_FOLDER, 'analysis_cache.pkl')
# Note: These paths will be updated in main() based on dynamic OUTPUT_FOLDER
CONTRIBUTION_REPORT_FILE = os.path.join(OUTPUT_FOLDER, 'sub_requirement_paper_contributions.md')
ORCHESTRATOR_STATE_FILE = os.path.join(OUTPUT_FOLDER, 'orchestrator_state.json')
DEEP_REVIEW_DIRECTIONS_FILE = os.path.join(OUTPUT_FOLDER, 'deep_review_directions.json')

# 3. External Scripts to call
# DEEP_REVIEWER_SCRIPT = 'Deep-Reviewer.py'
# JUDGE_SCRIPT = 'Judge.py'

# Create directories (output folder created in main() with dynamic value)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)  # Moved to main()
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Analysis configuration
ANALYSIS_CONFIG = {
    'MIN_PAPERS_FOR_ANALYSIS': 3,
    'QUALITY_WEIGHT_THRESHOLD': 0.7,
    'ENABLE_TREND_ANALYSIS': True,
    'ENABLE_NETWORK_ANALYSIS': True,
    'ENABLE_SEMANTIC_SEARCH': False,  # Disable for testing (CPU bottleneck on sentence transformer)
    'CACHE_RESULTS': True,
    'EXPORT_FORMATS': ['html', 'json', 'latex'],
    'API_CALLS_PER_MINUTE': 10,  # Conservative limit for gemini-2.5-flash (1000 RPM available)
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,
    'CONVERGENCE_THRESHOLD': 5.0  # 5% threshold
}


# --- HELPER CLASSES ---

class OrchestratorConfig:
    """Configuration for orchestrator execution"""
    
    def __init__(
        self,
        job_id: str,
        analysis_target: List[str],
        run_mode: str,
        skip_user_prompts: bool = True,
        progress_callback: Optional[callable] = None,
        log_callback: Optional[callable] = None,
        prompt_callback: Optional[callable] = None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize orchestrator configuration
        
        Args:
            job_id: Unique job identifier (use "terminal" for interactive mode)
            analysis_target: List of pillar names or ["ALL"]
            run_mode: "ONCE" (single pass) or "DEEP_LOOP" (iterative)
            skip_user_prompts: If True, skip interactive prompts
            progress_callback: Optional callback for progress updates
            log_callback: Optional callback for log messages
            prompt_callback: Optional async callback for interactive prompts
            output_dir: Optional custom output directory
        """
        self.job_id = job_id
        self.analysis_target = analysis_target
        self.run_mode = run_mode
        self.skip_user_prompts = skip_user_prompts
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.prompt_callback = prompt_callback
        self.output_dir = output_dir


@dataclass
class ProgressEvent:
    """Structured progress event for pipeline execution"""
    timestamp: str
    stage: str  # "initialization", "judge", "deep_review", "gap_analysis", "visualization", "finalization"
    phase: str  # "starting", "running", "complete", "error"
    message: str
    percentage: Optional[float] = None
    metadata: Optional[Dict] = None


class ETACalculator:
    """Estimates time to completion for pipeline jobs"""
    
    def __init__(self):
        self.stage_history = {}  # stage -> list of durations
    
    def record_stage_duration(self, stage: str, duration: float):
        """Record how long a stage took"""
        if stage not in self.stage_history:
            self.stage_history[stage] = []
        
        self.stage_history[stage].append(duration)
        
        # Keep last 10 measurements
        if len(self.stage_history[stage]) > 10:
            self.stage_history[stage].pop(0)
    
    def estimate_eta(
        self,
        current_stage: str,
        stage_started_at: datetime,
        remaining_stages: list
    ) -> Optional[timedelta]:
        """
        Estimate time to completion
        
        Args:
            current_stage: Stage currently executing
            stage_started_at: When current stage started
            remaining_stages: List of stages still to execute
        
        Returns:
            Estimated time remaining
        """
        # Estimate current stage remaining time
        if current_stage in self.stage_history:
            avg_duration = sum(self.stage_history[current_stage]) / len(self.stage_history[current_stage])
            elapsed = (datetime.utcnow() - stage_started_at).total_seconds()
            current_stage_remaining = max(0, avg_duration - elapsed)
        else:
            # No historical data, use default
            current_stage_remaining = 60  # 1 minute default
        
        # Estimate remaining stages
        remaining_time = current_stage_remaining
        
        for stage in remaining_stages:
            if stage in self.stage_history:
                remaining_time += sum(self.stage_history[stage]) / len(self.stage_history[stage])
            else:
                # Default estimates per stage
                defaults = {
                    "initialization": 30,
                    "judge": 180,  # 3 minutes
                    "deep_review": 300,  # 5 minutes
                    "gap_analysis": 240,  # 4 minutes
                    "visualization": 60,  # 1 minute
                    "finalization": 30
                }
                remaining_time += defaults.get(stage, 60)
        
        return timedelta(seconds=remaining_time)


class ProgressTracker:
    """Tracks and emits pipeline progress events"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.current_stage = None
        self.stages_completed = []
        self.stage_start_times = {}
        self.eta_calculator = ETACalculator()
        
        # Define pipeline stages and weights for percentage calculation
        self.stage_weights = {
            "initialization": 5,
            "judge": 15,
            "deep_review": 30,
            "gap_analysis": 35,
            "visualization": 10,
            "finalization": 5
        }
    
    def emit(self, stage: str, phase: str, message: str, **kwargs):
        """Emit a progress event"""
        # Track stage timing
        if phase == "starting":
            self.stage_start_times[stage] = datetime.utcnow()
            self.current_stage = stage
        elif phase == "complete" and stage in self.stage_start_times:
            # Record stage duration for ETA calculation
            duration = (datetime.utcnow() - self.stage_start_times[stage]).total_seconds()
            self.eta_calculator.record_stage_duration(stage, duration)
        
        # Calculate percentage
        percentage = self.calculate_percentage(stage, phase)
        
        # Calculate ETA
        eta = None
        if self.current_stage and self.current_stage in self.stage_start_times:
            remaining_stages = [
                s for s in self.stage_weights.keys()
                if s not in self.stages_completed and s != self.current_stage
            ]
            eta = self.eta_calculator.estimate_eta(
                self.current_stage,
                self.stage_start_times[self.current_stage],
                remaining_stages
            )
        
        # Create event with ETA in metadata
        metadata = kwargs.copy() if kwargs else {}
        if eta:
            metadata['eta_seconds'] = eta.total_seconds()
        
        event = ProgressEvent(
            timestamp=datetime.utcnow().isoformat(),
            stage=stage,
            phase=phase,
            message=message,
            percentage=percentage,
            metadata=metadata if metadata else None
        )
        
        # Call progress callback if provided
        if self.callback:
            self.callback(event)
        
        # Also log to file
        logger.info(f"[{stage}] {message}")
        
        # Also print to terminal if not suppressed
        if not kwargs.get('suppress_terminal'):
            safe_print(f"[{stage}] {message}")
    
    def calculate_percentage(self, stage: str, phase: str) -> float:
        """Calculate overall completion percentage"""
        total_weight = sum(self.stage_weights.values())
        
        # Calculate completed weight including the current stage if complete
        completed_weight = sum(
            self.stage_weights.get(s, 0) for s in self.stages_completed
        )
        
        if phase == "complete":
            # Add this stage's weight if it's being completed
            if stage not in self.stages_completed:
                completed_weight += self.stage_weights.get(stage, 0)
                # Mark as completed for future calculations
                self.stages_completed.append(stage)
        elif phase == "running":
            # Stage is partially complete (50%)
            completed_weight += self.stage_weights.get(stage, 0) * 0.5
        
        return (completed_weight / total_weight) * 100


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
        
        # Initialize sentence transformer only if semantic search enabled
        if ANALYSIS_CONFIG.get('ENABLE_SEMANTIC_SEARCH', False):
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("[SUCCESS] Sentence Transformer initialized.")
                safe_print("✅ Sentence Transformer initialized.")
            except Exception as e:
                logger.warning(f"[WARNING] Could not initialize Sentence Transformer: {e}")
                safe_print(f"⚠️ Could not initialize Sentence Transformer: {e}")
                self.embedder = None
        else:
            self.embedder = None
            logger.info("[INFO] Semantic search disabled (ENABLE_SEMANTIC_SEARCH=False)")
            safe_print("ℹ️ Semantic search disabled for faster testing")

    def rate_limit(self):
        """Implement rate limiting using global limiter"""
        global_limiter.wait_for_quota()

    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
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
        for attempt in range(ANALYSIS_CONFIG['RETRY_ATTEMPTS']):
            try:
                current_config_object = self.json_generation_config if is_json else self.text_generation_config
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt, config=current_config_object
                )
                response_text = response.text
                result = json.loads(response_text) if is_json else response_text
                self.cache[prompt_hash] = result
                # Record successful request
                global_limiter.record_request(success=True)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}. Response text: '{response_text[:500]}...'")
                # Categorize error
                category = global_limiter.categorize_error(e, response_text or "")
                action = global_limiter.get_action_for_error(category)
                global_limiter.record_request(success=False, error=e, response_text=response_text or "")
                
                if action == ErrorAction.SKIP_DOCUMENT:
                    logger.error(f"Skipping request due to {category.name}")
                    return None
                elif attempt < ANALYSIS_CONFIG['RETRY_ATTEMPTS'] - 1: 
                    time.sleep(ANALYSIS_CONFIG['RETRY_DELAY'])
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
                    logger.error(f"Skipping request due to {category.name}")
                    return None
                elif "429" in str(e):
                     logger.warning("Rate limit error detected by API, increasing sleep time.")
                     time.sleep(ANALYSIS_CONFIG['RETRY_DELAY'] * (attempt + 2))
                elif attempt < ANALYSIS_CONFIG['RETRY_ATTEMPTS'] - 1:
                     # Use delay from action's value tuple
                     _, delay = action.value
                     time.sleep(delay if delay > 0 else ANALYSIS_CONFIG['RETRY_DELAY'])
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
                 approved_deep_claims: List[Dict], config: Optional[Dict] = None):
        self.definitions = definitions
        self.database = database # The ResearchDatabase object
        self.all_db_records = all_db_records # The raw list of dicts from CSV
        self.api_manager = api_manager
        self.approved_deep_claims = approved_deep_claims # Approved claims from JSON DB
        self.cache = {}
        self.config = config or {}
        
        # Initialize gap analyzer for decay weighting
        from literature_review.analysis.gap_analyzer import GapAnalyzer
        self.gap_analyzer = GapAnalyzer(config=self.config)
        
        # Load version history for decay calculations
        self.version_history = self._load_version_history()
        
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
    
    def _load_version_history(self) -> Dict:
        """Load version history for publication years."""
        version_file = self.config.get('version_history_path', VERSION_HISTORY_FILE)
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load version history from {version_file}: {e}")
        return {}

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
            
            # Apply decay weighting if enabled
            analysis_results = self._apply_decay_weighting(analysis_results, pillar_name)
            
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
    
    def _apply_decay_weighting(self, analysis_results: Dict, pillar_name: str) -> Dict:
        """Apply evidence decay weighting to completeness scores."""
        if not self.gap_analyzer.decay_enabled:
            return analysis_results
        
        logger.info(f"   Applying evidence decay weighting for {pillar_name}...")
        
        for req_key, req_data in analysis_results.items():
            for sub_req, sub_req_data in req_data.items():
                raw_score = sub_req_data.get('completeness_percent', 0)
                papers = sub_req_data.get('contributing_papers', [])
                
                if papers:
                    # Apply decay weighting
                    final_score, metadata = self.gap_analyzer.apply_decay_weighting(
                        raw_score, papers, pillar_name, self.version_history
                    )
                    
                    # Update the score
                    sub_req_data['completeness_percent'] = final_score
                    
                    # Store metadata
                    sub_req_data['evidence_metadata'] = metadata
                else:
                    # No papers, no decay applied
                    sub_req_data['evidence_metadata'] = {
                        'raw_score': raw_score,
                        'final_score': raw_score,
                        'decay_applied': False,
                        'reason': 'no_papers'
                    }
        
        return analysis_results

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
    """Generate gap-closing search recommendations based on research gaps"""
    recommendations = []
    
    try:
        # Analyze each pillar for gaps
        for pillar_name, pillar_data in results.items():
            pillar_completeness = pillar_data.get('completeness', 0)
            
            # Process each sub-requirement
            for req_name, req_data in pillar_data.get('analysis', {}).items():
                for sub_req_name, sub_req_data in req_data.items():
                    completeness = sub_req_data.get('completeness_percent', 0)
                    
                    # Focus on gaps (< 50% complete) or areas with no coverage
                    if completeness < 50:
                        # Extract key terms from requirement name
                        req_short = sub_req_name.split(':')[-1].strip() if ':' in sub_req_name else sub_req_name
                        
                        # Determine priority based on completeness
                        if completeness == 0:
                            priority = "CRITICAL"
                            urgency = 1
                        elif completeness < 20:
                            priority = "HIGH"
                            urgency = 2
                        elif completeness < 50:
                            priority = "MEDIUM"
                            urgency = 3
                        else:
                            priority = "LOW"
                            urgency = 4
                        
                        # Generate search recommendations
                        recommendation = {
                            'pillar': pillar_name.split(':')[0],
                            'requirement': req_short,
                            'current_completeness': completeness,
                            'priority': priority,
                            'urgency': urgency,
                            'gap_description': sub_req_data.get('gap_analysis', 'No specific gap analysis available'),
                            'suggested_searches': []
                        }
                        
                        # Generate specific search queries based on the requirement
                        base_terms = req_short.lower()
                        
                        # Build search query variations
                        searches = []
                        
                        # Direct search
                        searches.append({
                            'query': f'"{req_short}"',
                            'rationale': 'Direct match for requirement topic',
                            'databases': ['Google Scholar', 'arXiv', 'PubMed', 'IEEE Xplore']
                        })
                        
                        # Add neuromorphic/AI context for AI pillars
                        if 'AI' in pillar_name or 'Bridge' in pillar_name:
                            searches.append({
                                'query': f'neuromorphic AND ({req_short})',
                                'rationale': 'Neuromorphic computing context',
                                'databases': ['arXiv', 'IEEE Xplore', 'Frontiers']
                            })
                            searches.append({
                                'query': f'"spiking neural networks" AND ({req_short})',
                                'rationale': 'SNN-specific implementations',
                                'databases': ['arXiv', 'IEEE Xplore']
                            })
                        
                        # Add biological context for biological pillars
                        if 'Biological' in pillar_name:
                            searches.append({
                                'query': f'neuroscience AND ({req_short})',
                                'rationale': 'Neuroscience research context',
                                'databases': ['PubMed', 'Nature', 'Science Direct']
                            })
                            searches.append({
                                'query': f'"neural mechanisms" AND ({req_short})',
                                'rationale': 'Neural mechanism studies',
                                'databases': ['PubMed', 'Frontiers in Neuroscience']
                            })
                        
                        # Add review/survey searches for critical gaps
                        if priority in ['CRITICAL', 'HIGH']:
                            searches.append({
                                'query': f'review AND ({req_short})',
                                'rationale': 'Literature reviews for comprehensive coverage',
                                'databases': ['Google Scholar', 'Annual Reviews']
                            })
                        
                        recommendation['suggested_searches'] = searches
                        recommendations.append(recommendation)
        
        # Sort by urgency (critical first) then by completeness (lowest first)
        recommendations.sort(key=lambda x: (x['urgency'], x['current_completeness']))
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return []

def generate_executive_summary(results: Dict, database: ResearchDatabase, output_folder: str):
    """Generate an executive summary of the gap analysis results"""
    try:
        summary_path = os.path.join(output_folder, "executive_summary.md")
        
        # Calculate overall statistics
        pillar_scores = {name: data.get('completeness', 0) for name, data in results.items()}
        avg_completeness = np.mean(list(pillar_scores.values())) if pillar_scores else 0
        total_papers = len(database.db) if database.db is not None else 0
        
        # Identify critical gaps
        critical_gaps = identify_critical_gaps(results)
        
        # Build summary content
        content = [
            "# Gap Analysis Executive Summary\n",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**Total Papers Analyzed:** {total_papers}",
            f"**Average Research Completeness:** {avg_completeness:.1f}%\n",
            "---\n",
            "## Overall Completeness by Pillar\n"
        ]
        
        # Add pillar completeness table
        content.append("| Pillar | Completeness | Status |")
        content.append("|:-------|-------------:|:-------|")
        for pillar_name, score in sorted(pillar_scores.items(), key=lambda x: x[1], reverse=True):
            status = "🟢 Good" if score >= 70 else "🟡 Moderate" if score >= 30 else "🔴 Critical"
            pillar_short = pillar_name.split(':')[0]
            content.append(f"| {pillar_short} | {score:.1f}% | {status} |")
        
        content.append("\n## Critical Research Gaps\n")
        if critical_gaps:
            content.append("The following areas require immediate attention:\n")
            for i, gap in enumerate(critical_gaps[:10], 1):
                content.append(f"{i}. {gap}")
        else:
            content.append("No critical gaps identified (all areas > 30% complete).\n")
        
        content.append("\n## Key Findings\n")
        
        # Identify strongest and weakest areas
        if pillar_scores:
            strongest = max(pillar_scores.items(), key=lambda x: x[1])
            weakest = min(pillar_scores.items(), key=lambda x: x[1])
            content.append(f"- **Strongest Area:** {strongest[0]} ({strongest[1]:.1f}% complete)")
            content.append(f"- **Weakest Area:** {weakest[0]} ({weakest[1]:.1f}% complete)")
        
        # Count total sub-requirements and their status
        total_subs = 0
        complete_subs = 0
        partial_subs = 0
        missing_subs = 0
        
        for pillar_data in results.values():
            for req_data in pillar_data.get('analysis', {}).values():
                for sub_data in req_data.values():
                    total_subs += 1
                    completeness = sub_data.get('completeness_percent', 0)
                    if completeness >= 80:
                        complete_subs += 1
                    elif completeness > 0:
                        partial_subs += 1
                    else:
                        missing_subs += 1
        
        content.append(f"\n### Sub-Requirement Coverage ({total_subs} total)")
        content.append(f"- ✅ **Well-Covered (≥80%):** {complete_subs} ({100*complete_subs/total_subs:.1f}%)")
        content.append(f"- 🟡 **Partially Covered (1-79%):** {partial_subs} ({100*partial_subs/total_subs:.1f}%)")
        content.append(f"- 🔴 **Not Covered (0%):** {missing_subs} ({100*missing_subs/total_subs:.1f}%)")
        
        content.append("\n## Recommendations\n")
        content.append("1. **Immediate Actions:** Focus research efforts on critically low completeness areas (< 30%)")
        content.append("2. **Deep Review:** Conduct targeted literature search for sub-requirements with 0% coverage")
        content.append("3. **Validation:** Review high-completeness claims to ensure quality and accuracy")
        content.append("4. **Gap Closure:** Prioritize filling gaps in foundational pillars (Biological systems)")
        
        content.append("\n---\n")
        content.append("*For detailed analysis, see the full gap_analysis_report.json and pillar waterfall visualizations.*\n")
        
        # Write to file
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        logger.info(f"Executive summary generated: {summary_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate executive summary: {e}")
        return False
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

def save_orchestrator_state(state_file: str, previous_results: Dict, score_history: Dict, stage: str = "final"):
    """Saves the current run state, results, and score history with stage tracking."""
    state = {
        "last_run_timestamp": datetime.now().isoformat(),
        "last_completed_stage": stage,  # Track which stage completed
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
        logger.info(f"Successfully saved orchestrator state to {state_file} (stage: {stage})")
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

async def get_user_analysis_target_async(
    pillar_definitions: Dict,
    prompt_callback: Optional[Callable] = None
) -> Tuple[List[str], str]:
    """
    Get analysis target from user (async version for dashboard)
    
    Args:
        pillar_definitions: Available pillars
        prompt_callback: Async callback for prompts (if None, uses terminal input)
    
    Returns:
        (pillar_list, run_mode)
    """
    # Filter out metadata sections that can't be analyzed
    metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
    all_keys = list(pillar_definitions.keys())
    analyzable_pillars = [k for k in all_keys if k not in metadata_sections]
    
    if prompt_callback is None:
        # Terminal mode - original behavior
        safe_print("\n--- No new data detected ---")
        safe_print("What would you like to re-assess?")
        
        for i, name in enumerate(analyzable_pillars, 1):
            safe_print(f"  {i}. {name.split(':')[0]}")
        safe_print(f"\n  ALL - Run analysis on all pillars (one pass)")
        safe_print(f"  DEEP - Run iterative deep-review loop on all pillars")
        safe_print(f"  NONE - Exit (default)")
        
        choice = input(f"Enter choice (1-{len(analyzable_pillars)}, ALL, DEEP, NONE): ").strip().upper()
    else:
        # Dashboard mode - use prompt callback
        choice = await prompt_callback(
            prompt_type="pillar_selection",
            prompt_data={
                "message": "Select pillars to analyze",
                "options": analyzable_pillars,
                "allow_all": True,
                "allow_deep": True,
                "allow_none": True
            }
        )
    
    # Parse response - handle both string and list responses
    if isinstance(choice, list):
        # Multi-select: ["P1: Pillar 1", "P3: Pillar 3", "P5: Pillar 5"]
        # Validate that all selected pillars exist
        valid_selections = [p for p in choice if p in analyzable_pillars]
        if not valid_selections:
            safe_print("Invalid pillar selection. Exiting.")
            return [], "EXIT"
        return valid_selections, "ONCE"
    
    # String responses (special options or single pillar)
    if not choice or choice == "NONE":
        return [], "EXIT"
    if choice == "ALL":
        return analyzable_pillars, "ONCE"
    if choice == "DEEP":
        return analyzable_pillars, "DEEP_LOOP"
    
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(analyzable_pillars):
            return [analyzable_pillars[choice_idx]], "ONCE"
    except ValueError:
        pass
    
    safe_print("Invalid choice. Exiting.")
    return [], "EXIT"


def get_user_analysis_target(
    pillar_definitions: Dict,
    prompt_callback: Optional[Callable] = None
) -> Tuple[List[str], str]:
    """
    Asks the user what to analyze. Returns (pillar_list, run_mode).
    
    Args:
        pillar_definitions: Available pillars
        prompt_callback: Optional async callback for prompts (dashboard mode)
    
    Returns:
        (pillar_list, run_mode)
    """
    if prompt_callback is None:
        # Terminal mode - use sync code
        safe_print("\n--- No new data detected ---")
        safe_print("What would you like to re-assess?")

        # Filter out metadata sections that can't be analyzed
        metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
        all_keys = list(pillar_definitions.keys())
        analyzable_pillars = [k for k in all_keys if k not in metadata_sections]
        
        # Only show analyzable pillars to user
        for i, name in enumerate(analyzable_pillars, 1):
            safe_print(f"  {i}. {name.split(':')[0]}")
        safe_print(f"\n  ALL - Run analysis on all pillars (one pass)")
        safe_print(f"  DEEP - Run iterative deep-review loop on all pillars")
        safe_print(f"  NONE - Exit (default)")

        choice = input(f"Enter choice (1-{len(analyzable_pillars)}, ALL, DEEP, NONE): ").strip().upper()

        if not choice or choice == "NONE":
            return [], "EXIT"
        if choice == "ALL":
            return analyzable_pillars, "ONCE"
        if choice == "DEEP":
            return analyzable_pillars, "DEEP_LOOP"
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(analyzable_pillars):
                selected = analyzable_pillars[choice_idx]
                return [selected], "ONCE"
        except ValueError:
            pass

        safe_print("Invalid choice. Exiting.")
        return [], "EXIT"
    else:
        # Dashboard mode - run async callback
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                get_user_analysis_target_async(pillar_definitions, prompt_callback)
            )
        finally:
            loop.close()



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


# --- WEIGHTED GAP ANALYSIS FUNCTIONS (Task Card #16) ---

def calculate_weighted_gap_score(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """
    Calculate gap scores weighted by evidence quality.
    
    Prioritizes filling gaps where evidence is weak or missing.
    """
    gap_scores = {}
    
    for pillar_name, pillar_data in pillar_definitions.items():
        for req_key, req_data in pillar_data.get("requirements", {}).items():
            for sub_req in req_data:
                # Get all claims for this sub-requirement
                claims = db[db["Requirement(s)"].str.contains(sub_req, na=False)]
                
                if claims.empty:
                    # No evidence: highest priority
                    gap_scores[sub_req] = {
                        "priority": 1.0,
                        "reason": "no_evidence",
                        "avg_quality": 0.0,
                        "claim_count": 0
                    }
                else:
                    # Extract quality scores
                    quality_scores = []
                    for _, row in claims.iterrows():
                        req_list_str = row.get("Requirement(s)", "[]")
                        if isinstance(req_list_str, str):
                            try:
                                req_list = json.loads(req_list_str)
                            except json.JSONDecodeError:
                                continue
                        else:
                            req_list = req_list_str if isinstance(req_list_str, list) else []
                        
                        for claim in req_list:
                            if sub_req in claim.get("sub_requirement", ""):
                                quality = claim.get("evidence_quality", {})
                                composite = quality.get("composite_score", 3.0)
                                quality_scores.append(composite)
                    
                    avg_quality = np.mean(quality_scores) if quality_scores else 3.0
                    
                    # Priority inversely proportional to quality
                    # Low quality (1.0) = High priority (1.0)
                    # High quality (5.0) = Low priority (0.2)
                    priority = 1.0 - ((avg_quality - 1.0) / 4.0)
                    
                    gap_scores[sub_req] = {
                        "priority": priority,
                        "reason": "low_quality_evidence" if avg_quality < 3.5 else "sufficient_evidence",
                        "avg_quality": avg_quality,
                        "claim_count": len(quality_scores)
                    }
    
    return gap_scores


def plot_evidence_quality_distribution(db: pd.DataFrame, output_file: str):
    """Generate histogram of evidence quality scores."""
    import matplotlib.pyplot as plt
    
    quality_scores = []
    for _, row in db.iterrows():
        req_list_str = row.get("Requirement(s)", "[]")
        if isinstance(req_list_str, str):
            try:
                req_list = json.loads(req_list_str)
            except json.JSONDecodeError:
                continue
        else:
            req_list = req_list_str if isinstance(req_list_str, list) else []
        
        for claim in req_list:
            quality = claim.get("evidence_quality", {})
            score = quality.get("composite_score")
            if score:
                quality_scores.append(score)
    
    if not quality_scores:
        logger.warning("No quality scores found to plot.")
        return
    
    plt.figure(figsize=(10, 6))
    plt.hist(quality_scores, bins=20, edgecolor='black', alpha=0.7)
    plt.xlabel("Composite Evidence Quality Score")
    plt.ylabel("Number of Claims")
    plt.title("Distribution of Evidence Quality Scores")
    plt.axvline(x=3.0, color='r', linestyle='--', label='Approval Threshold')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    logger.info(f"Evidence quality distribution plot saved to {output_file}")

# --- END WEIGHTED GAP ANALYSIS FUNCTIONS ---


# --- TEMPORAL COHERENCE ANALYSIS FUNCTIONS (Task Card #19) ---

def classify_maturity(evidence_span: int, total_papers: int, recent_papers: int) -> str:
    """
    Classify maturity level of evidence for a sub-requirement.
    
    Args:
        evidence_span: Years between earliest and latest evidence
        total_papers: Total number of papers
        recent_papers: Number of papers in last 3 years
    
    Returns:
        Maturity level: "emerging", "growing", "established", or "mature"
    """
    if evidence_span < 2 and total_papers < 5:
        return "emerging"
    elif evidence_span < 5 and total_papers < 10:
        return "growing"
    elif evidence_span >= 5 and total_papers >= 10:
        if total_papers >= 20 and recent_papers >= 5:
            return "mature"
        return "established"
    else:
        return "growing"


def analyze_evidence_evolution(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """
    Analyze how evidence for each sub-requirement has evolved over time.
    
    Args:
        db: Research database DataFrame
        pillar_definitions: Dictionary of pillar definitions with requirements
    
    Returns:
        Dictionary mapping sub-requirements to temporal analysis:
        {
            "Sub-2.1.1": {
                "earliest_evidence": 2018,
                "latest_evidence": 2024,
                "evidence_span_years": 6,
                "total_papers": 15,
                "recent_papers": 8,
                "evidence_count_by_year": {2018: 2, 2020: 5, 2024: 8},
                "quality_trend": "improving",  # improving|stable|declining|unknown
                "maturity_level": "established",  # emerging|growing|established|mature
                "consensus_strength": "strong",  # strong|moderate|weak|none|unknown
                "recent_activity": True  # 3+ papers in last 3 years
            },
            ...
        }
    """
    from datetime import datetime
    
    temporal_analysis = {}
    current_year = datetime.now().year
    
    for pillar_name, pillar_data in pillar_definitions.items():
        # Skip non-pillar entries
        if not isinstance(pillar_data, dict) or "requirements" not in pillar_data:
            continue
            
        for req_key, req_data in pillar_data.get("requirements", {}).items():
            for sub_req_list in req_data:
                # Handle both single sub-reqs and comma-separated lists
                for sub_req in sub_req_list.split(','):
                    sub_req = sub_req.strip()
                    
                    # Get all claims for this sub-requirement
                    claims = db[db["Requirement(s)"].str.contains(sub_req, na=False)]
                    
                    if claims.empty:
                        continue
                    
                    # Extract publication years
                    years = claims["PUBLICATION_YEAR"].dropna()
                    years = years[years > 1900]  # Filter out invalid years
                    years = years.astype(int)
                    
                    if len(years) == 0:
                        continue
                    
                    # Count by year
                    year_counts = years.value_counts().sort_index().to_dict()
                    
                    # Analyze quality trend (if composite scores available)
                    quality_trend = "unknown"
                    if "EVIDENCE_COMPOSITE_SCORE" in claims.columns:
                        # Group by year and calculate mean scores
                        scores_by_year = claims.groupby("PUBLICATION_YEAR")["EVIDENCE_COMPOSITE_SCORE"].mean()
                        scores_by_year = scores_by_year[scores_by_year.index > 1900]
                        
                        if len(scores_by_year) >= 3:  # Need 3+ years for trend
                            # Linear regression to detect trend
                            from scipy.stats import linregress
                            slope, intercept, r_value, p_value, std_err = linregress(
                                scores_by_year.index, scores_by_year.values
                            )
                            
                            if p_value < 0.05:  # Statistically significant
                                if slope > 0.1:
                                    quality_trend = "improving"
                                elif slope < -0.1:
                                    quality_trend = "declining"
                                else:
                                    quality_trend = "stable"
                            else:
                                quality_trend = "stable"
                    
                    # Determine maturity level
                    evidence_span = int(years.max() - years.min())
                    total_papers = len(claims)
                    recent_papers = len(claims[claims["PUBLICATION_YEAR"] >= current_year - 3])
                    
                    maturity = classify_maturity(evidence_span, total_papers, recent_papers)
                    
                    # Check for consensus (low score variance = consensus)
                    consensus = "unknown"
                    if "EVIDENCE_COMPOSITE_SCORE" in claims.columns:
                        score_std = claims["EVIDENCE_COMPOSITE_SCORE"].std()
                        if score_std < 0.5:
                            consensus = "strong"
                        elif score_std < 1.0:
                            consensus = "moderate"
                        elif score_std < 1.5:
                            consensus = "weak"
                        else:
                            consensus = "none"
                    
                    temporal_analysis[sub_req] = {
                        "earliest_evidence": int(years.min()),
                        "latest_evidence": int(years.max()),
                        "evidence_span_years": evidence_span,
                        "total_papers": total_papers,
                        "recent_papers": recent_papers,
                        "evidence_count_by_year": year_counts,
                        "quality_trend": quality_trend,
                        "maturity_level": maturity,
                        "consensus_strength": consensus,
                        "recent_activity": recent_papers >= 3  # Active if 3+ papers in last 3 years
                    }
    
    return temporal_analysis

# --- END TEMPORAL COHERENCE ANALYSIS FUNCTIONS ---


# --- MAIN EXECUTION (MODIFIED) ---
def main(config: Optional[OrchestratorConfig] = None, output_folder: Optional[str] = None):
    """
    Main orchestrator entry point
    
    Args:
        config: Optional configuration for programmatic execution.
                If None, runs in interactive terminal mode.
        output_folder: Custom output directory (overrides default and config)
    """
    # Set global OUTPUT_FOLDER based on parameter or config
    global OUTPUT_FOLDER
    
    if output_folder:
        # Explicit parameter takes highest priority
        OUTPUT_FOLDER = output_folder
    elif config and hasattr(config, 'output_dir') and config.output_dir:
        # Config object has output_dir
        OUTPUT_FOLDER = config.output_dir
    elif config and isinstance(config, dict) and config.get('output_dir'):
        # Config dict has output_dir
        OUTPUT_FOLDER = config['output_dir']
    else:
        # Use environment variable or default
        OUTPUT_FOLDER = os.getenv('LITERATURE_REVIEW_OUTPUT_DIR', 'gap_analysis_output')
    
    # Create output directory
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Update dependent file paths
    global CONTRIBUTION_REPORT_FILE, ORCHESTRATOR_STATE_FILE, DEEP_REVIEW_DIRECTIONS_FILE
    CONTRIBUTION_REPORT_FILE = os.path.join(OUTPUT_FOLDER, 'sub_requirement_paper_contributions.md')
    ORCHESTRATOR_STATE_FILE = os.path.join(OUTPUT_FOLDER, 'orchestrator_state.json')
    DEEP_REVIEW_DIRECTIONS_FILE = os.path.join(OUTPUT_FOLDER, 'deep_review_directions.json')
    
    logger.info("\n" + "=" * 80)
    logger.info("ENHANCED GAP ANALYSIS ORCHESTRATOR v3.6 (Pre-Analysis Judge Run)")
    logger.info(f"Output Directory: {OUTPUT_FOLDER}")
    logger.info("=" * 80)
    global_start_time = time.time()

    # Initialize progress tracker
    progress_tracker = ProgressTracker(
        callback=config.progress_callback if config else None
    )
    
    progress_tracker.emit("initialization", "starting", "Starting orchestrator pipeline...")

    # --- 1. Load Static Definitions & State ---
    progress_tracker.emit("initialization", "running", "Loading pillar definitions...")
    try:
        with open(DEFINITIONS_FILE, 'r') as f:
            definitions = json.load(f)
        logger.info(f"[SUCCESS] Loaded {len(definitions)} pillar definitions")
        progress_tracker.emit(
            "initialization", 
            "complete", 
            f"Loaded {len(definitions)} pillar definitions"
        )
    except FileNotFoundError:
        logger.error(f"[ERROR] Definitions file not found: {DEFINITIONS_FILE}. Exiting.")
        safe_print(f"❌ Definitions file not found: {DEFINITIONS_FILE}. Exiting.")
        progress_tracker.emit("initialization", "error", f"Definitions file not found: {DEFINITIONS_FILE}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Error decoding JSON from {DEFINITIONS_FILE}. Exiting.")
        safe_print(f"❌ Error decoding JSON from {DEFINITIONS_FILE}. Exiting.")
        progress_tracker.emit("initialization", "error", f"Error decoding JSON: {e}")
        return

    last_run_state, previous_results, score_history = load_orchestrator_state(ORCHESTRATOR_STATE_FILE)
    
    # Load pipeline configuration for decay weighting
    pipeline_config = {}
    try:
        with open('pipeline_config.json', 'r') as f:
            pipeline_config = json.load(f)
        logger.info("[SUCCESS] Loaded pipeline configuration")
    except Exception as e:
        logger.warning(f"Could not load pipeline_config.json: {e}. Using defaults.")

    # --- 2. Determine Run Mode & Run Initial Judge ---
    has_new_data = check_for_new_data(last_run_state)
    analysis_target_pillars = []
    run_mode = "" # "ONCE" or "DEEP_LOOP" or "EXIT"
    run_initial_judge = False

    # Use config if provided (programmatic mode), otherwise use interactive mode
    if config is not None and config.skip_user_prompts:
        # Programmatic mode from dashboard
        analysis_target_pillars = config.analysis_target
        run_mode = config.run_mode
        
        # Log via callback if available
        if config.log_callback:
            config.log_callback(f"Starting job {config.job_id} with mode {run_mode}")
        
        # For programmatic mode, always run initial judge if there's new data
        if has_new_data:
            run_initial_judge = True
        
        logger.info(f"Running in programmatic mode: job_id={config.job_id}, mode={run_mode}, pillars={analysis_target_pillars}")
    elif config is not None and not config.skip_user_prompts and config.prompt_callback:
        # Dashboard mode with prompts enabled
        analysis_target_pillars = config.analysis_target
        
        # Prompt for run_mode if not set in config
        if not config.run_mode or config.run_mode == "":
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                run_mode_str = loop.run_until_complete(
                    config.prompt_callback(
                        prompt_type="run_mode",
                        prompt_data={
                            "message": "Select analysis mode",
                            "options": ["ONCE", "DEEP_LOOP"],
                            "default": "ONCE"
                        }
                    )
                )
                run_mode = run_mode_str.upper()
                logger.info(f"User selected run_mode: {run_mode}")
            finally:
                loop.close()
        else:
            run_mode = config.run_mode
        
        # Log via callback if available
        if config.log_callback:
            config.log_callback(f"Starting job {config.job_id} with mode {run_mode}")
        
        # For dashboard mode, run initial judge if there's new data
        if has_new_data:
            run_initial_judge = True
        
        logger.info(f"Running in dashboard mode with prompts: job_id={config.job_id}, mode={run_mode}, pillars={analysis_target_pillars}")
    elif has_new_data:
        safe_print("📬 New data detected in CSV or JSON. Running Judge to validate claims before analysis.")
        run_initial_judge = True
        # Filter out metadata sections (not analyzable pillars)
        metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
        analysis_target_pillars = [k for k in definitions.keys() if k not in metadata_sections]
        run_mode = "DEEP_LOOP"
    else:
        # Interactive mode - may use prompt callback if provided in config
        prompt_callback = config.prompt_callback if config else None
        analysis_target_pillars, run_mode = get_user_analysis_target(definitions, prompt_callback)
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
        progress_tracker.emit("judge", "starting", "Running Judge to validate claims...")
        if not judge.main():
            logger.critical("Initial Judge run failed. Halting.")
            safe_print("❌ Initial Judge run failed. Halting.")
            progress_tracker.emit("judge", "error", "Judge validation failed")
            return
        safe_print("✅ Initial data validated by Judge.")
        progress_tracker.emit("judge", "complete", "Claims validated successfully")
        
        # ✅ CHECKPOINT: Save state after judge completes
        save_orchestrator_state(ORCHESTRATOR_STATE_FILE, previous_results, score_history, stage="judge_complete")
        logger.info("✓ Checkpoint saved after Judge completion")
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
        
        progress_tracker.emit(
            "gap_analysis",
            "running",
            f"Starting gap analysis iteration {iteration_count}",
            iteration=iteration_count
        )

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
            all_db_records, approved_deep_claims, pipeline_config
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
        
        progress_tracker.emit(
            "gap_analysis",
            "running",
            f"Iteration {iteration_count} complete",
            iteration=iteration_count,
            completeness_scores={k: v.get('completeness', 0) for k, v in all_results.items()}
        )
        
        # ✅ CHECKPOINT: Save state after each gap analysis iteration
        save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history, 
                               stage=f"gap_analysis_iteration_{iteration_count}")
        logger.info(f"✓ Checkpoint saved after iteration {iteration_count}")

        if score_diffs:
            safe_print("\n--- Score Changes This Iteration ---")
            for sub_req, diff in score_diffs.items():
                safe_print(f"  📈 {sub_req.split(':')[0]}: {diff['prev']:.1f}% -> {diff['curr']:.1f}% (+{diff['delta']:.1f}%)")

        # --- 4d. Decide: Loop Again or Exit? ---
        if run_mode == "ONCE":
            safe_print("\nAnalysis complete (single pass mode).")
            break

        if needs_new_loop:
            # Ask user if they want to continue (if prompt callback is available)
            should_continue = True
            if config and config.prompt_callback and not config.skip_user_prompts:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Count gaps to show user
                    gap_count = len(directions) if isinstance(directions, dict) else 0
                    
                    continue_response = loop.run_until_complete(
                        config.prompt_callback(
                            prompt_type="continue",
                            prompt_data={
                                "message": f"Iteration {iteration_count} complete. Continue deep review loop?",
                                "iteration": iteration_count,
                                "gap_count": gap_count,
                                "options": ["yes", "no"],
                                "default": "yes",
                                "details": f"Found {gap_count} gaps to address. Continue with deep review?"
                            }
                        )
                    )
                    should_continue = continue_response.lower() in ["yes", "y", "true"]
                    logger.info(f"User continue decision: {continue_response} -> {should_continue}")
                finally:
                    loop.close()
            
            if not should_continue:
                safe_print("\n⏸️ User chose to stop deep loop")
                logger.info("Deep loop stopped by user choice")
                progress_tracker.emit("gap_analysis", "complete", "Deep loop stopped by user")
                break
            
            safe_print("\nConvergence not met. Running new Deep Review loop...")
            write_deep_review_directions(DEEP_REVIEW_DIRECTIONS_FILE, directions)

            progress_tracker.emit("deep_review", "starting", f"Running Deep Review for iteration {iteration_count + 1}...")
            if not deep_reviewer.main():
                safe_print("❌ Deep Reviewer failed. Halting loop.")
                progress_tracker.emit("deep_review", "error", "Deep Reviewer failed")
                break
            progress_tracker.emit("deep_review", "complete", "Deep Review completed successfully")
            
            progress_tracker.emit("judge", "starting", "Validating new claims from Deep Review...")
            if not judge.main():
                safe_print("❌ Judge failed. Halting loop.")
                progress_tracker.emit("judge", "error", "Judge validation failed")
                break
            progress_tracker.emit("judge", "complete", "New claims validated")

            previous_results = all_results.copy()
            # Filter out metadata sections (not analyzable pillars)
            metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
            analysis_target_pillars = [k for k in definitions.keys() if k not in metadata_sections]
        else:
            safe_print("\n✅ Convergence Reached. No sub-requirement changed by > 5%.")
            write_deep_review_directions(DEEP_REVIEW_DIRECTIONS_FILE, {}) # Clear directions
            progress_tracker.emit("gap_analysis", "complete", "Gap analysis converged")
            break

    # --- 5. Post-Loop: Generate Final Reports ---
    logger.info("\n" + "=" * 80)
    logger.info("Analysis loop complete. Generating final reports...")
    safe_print("\n--- 📊 Generating Final Reports ---")
    
    progress_tracker.emit("visualization", "starting", "Generating visualizations and reports...")

    # Track visualization generation success
    visualization_errors = []
    
    # Generate pillar waterfall plots
    logger.info("Generating pillar waterfall visualizations...")
    for pillar_name, pillar_data in all_results.items():
        try:
            output_path = os.path.join(OUTPUT_FOLDER, f"waterfall_{pillar_name.split(':')[0]}.html")
            logger.info(f"  Creating waterfall for {pillar_name}...")
            plotter.create_waterfall_plot(
                pillar_name, pillar_data.get('waterfall_data', []),
                output_path
            )
            logger.info(f"  ✅ Waterfall saved: {output_path}")
        except Exception as e:
            error_msg = f"Failed to create waterfall for {pillar_name}: {e}"
            logger.error(error_msg)
            visualization_errors.append(error_msg)
            safe_print(f"  ⚠️ {error_msg}")
    
    # Generate radar plot
    if radar_data:
        try:
            logger.info("Generating research gap radar plot...")
            radar_path = os.path.join(OUTPUT_FOLDER, "_OVERALL_Research_Gap_Radar.html")
            plotter.create_radar_plot(
                radar_data, radar_path,
                velocity_data=velocity_data if trend_analyzer else None
            )
            logger.info(f"  ✅ Radar plot saved: {radar_path}")
            safe_print("  ✅ Research gap radar generated.")
        except Exception as e:
            error_msg = f"Failed to create radar plot: {e}"
            logger.error(error_msg)
            visualization_errors.append(error_msg)
            safe_print(f"  ⚠️ {error_msg}")
    
    # Generate paper network visualization
    if ANALYSIS_CONFIG.get('ENABLE_NETWORK_ANALYSIS') and database_df_obj and database_df_obj.paper_network:
        try:
            logger.info("Generating paper network visualization...")
            network_path = os.path.join(OUTPUT_FOLDER, "_Paper_Network.html")
            plotter.create_network_plot(
                database_df_obj.paper_network,
                network_path
            )
            logger.info(f"  ✅ Network plot saved: {network_path}")
            safe_print("  ✅ Paper network visualization generated.")
        except Exception as e:
            error_msg = f"Failed to create network plot: {e}"
            logger.error(error_msg)
            visualization_errors.append(error_msg)
            safe_print(f"  ⚠️ {error_msg}")
    
    # Generate research trends visualization
    if trend_analyzer:
        try:
            logger.info("Generating research trends visualization...")
            trends_path = os.path.join(OUTPUT_FOLDER, "_Research_Trends.html")
            trend_data = trend_analyzer.analyze_trends(definitions)
            if trend_data:
                plotter.create_trend_plot(trend_data, trends_path)
                logger.info(f"  ✅ Trends plot saved: {trends_path}")
                safe_print("  ✅ Research trends visualization generated.")
        except Exception as e:
            error_msg = f"Failed to create trends plot: {e}"
            logger.error(error_msg)
            visualization_errors.append(error_msg)
            safe_print(f"  ⚠️ {error_msg}")

    if score_history["iteration_timestamps"]:
        logger.info("Generating convergence plots...")
        try:
            # Check if convergence plots function exists
            if hasattr(plotter, 'create_convergence_plots'):
                plotter.create_convergence_plots(
                    score_history, definitions,
                    os.path.join(OUTPUT_FOLDER, "_OVERALL_Score_Convergence.html")
                )
                logger.info("  ✅ Convergence plots generated.")
                safe_print("  ✅ Convergence plots generated.")
            else:
                logger.warning("create_convergence_plots not found in plotter module. Skipping.")
                safe_print("  ⚠️ Convergence plots not available (function not implemented).")
        except Exception as e:
            error_msg = f"Failed to create convergence plots: {e}"
            logger.error(error_msg)
            visualization_errors.append(error_msg)
            safe_print(f"  ⚠️ {error_msg}")

    # Generate JSON report
    logger.info("Generating JSON report...")
    if 'json' in ANALYSIS_CONFIG['EXPORT_FORMATS']:
        try:
            report_generator.generate_json_report(all_results, "gap_analysis_report.json")
            json_path = os.path.join(OUTPUT_FOLDER, "gap_analysis_report.json")
            if os.path.exists(json_path):
                logger.info(f"  ✅ JSON report saved: {json_path}")
                safe_print("  ✅ JSON report generated.")
            else:
                error_msg = "JSON report function completed but file not found"
                logger.warning(error_msg)
                visualization_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to generate JSON report: {e}"
            logger.error(error_msg)
            visualization_errors.append(error_msg)
            safe_print(f"  ⚠️ {error_msg}")
    
    # Generate evidence decay report
    logger.info("Generating evidence decay report...")
    try:
        from literature_review.utils.evidence_decay import generate_decay_report
        
        # Load config to check if evidence decay is enabled
        config_enabled = True
        try:
            with open('pipeline_config.json', 'r') as f:
                config = json.load(f)
                config_enabled = config.get('evidence_decay', {}).get('enabled', True)
        except Exception:
            pass
        
        if config_enabled:
            decay_report = generate_decay_report(
                review_log='review_log.json',
                gap_analysis=os.path.join(OUTPUT_FOLDER, 'gap_analysis_report.json'),
                output_file=os.path.join(OUTPUT_FOLDER, 'evidence_decay.json')
            )
            logger.info(f"  ✅ Evidence decay report saved")
            safe_print("  ✅ Evidence decay analysis generated.")
        else:
            logger.info("  ℹ️  Evidence decay analysis disabled in config")
    except Exception as e:
        error_msg = f"Failed to generate evidence decay report: {e}"
        logger.warning(error_msg)
        safe_print(f"  ⚠️ {error_msg}")

    # Generate contribution markdown report
    logger.info("Generating contribution markdown report...")
    try:
        report_generator.generate_contribution_report_md(all_results)
        if os.path.exists(CONTRIBUTION_REPORT_FILE):
            logger.info(f"  ✅ Contribution report saved: {CONTRIBUTION_REPORT_FILE}")
            safe_print("  ✅ Contribution report generated.")
        else:
            error_msg = "Contribution report function completed but file not found"
            logger.warning(error_msg)
            visualization_errors.append(error_msg)
    except Exception as e:
        error_msg = f"Failed to generate contribution report: {e}"
        logger.error(error_msg)
        visualization_errors.append(error_msg)
        safe_print(f"  ⚠️ {error_msg}")

    # Generate executive summary
    logger.info("Generating executive summary...")
    try:
        database_df_obj = ResearchDatabase(RESEARCH_DB_FILE) # Re-load for final summary
        generate_executive_summary(all_results, database_df_obj, OUTPUT_FOLDER)
        summary_path = os.path.join(OUTPUT_FOLDER, "executive_summary.md")
        if os.path.exists(summary_path):
            logger.info(f"  ✅ Executive summary saved: {summary_path}")
            safe_print("  ✅ Executive summary generated.")
        else:
            logger.warning("Executive summary function completed but no file generated (may be a stub)")
            safe_print("  ⚠️ Executive summary not available (function not implemented).")
    except Exception as e:
        error_msg = f"Failed to generate executive summary: {e}"
        logger.error(error_msg)
        visualization_errors.append(error_msg)
        safe_print(f"  ⚠️ {error_msg}")
    
    # Generate gap-closing search recommendations
    logger.info("Generating gap-closing search recommendations...")
    try:
        database_df_obj = ResearchDatabase(RESEARCH_DB_FILE) # Re-load if needed
        recommendations = generate_recommendations(all_results, database_df_obj)
        
        if recommendations:
            # Save as JSON
            rec_json_path = os.path.join(OUTPUT_FOLDER, "suggested_searches.json")
            with open(rec_json_path, 'w', encoding='utf-8') as f:
                json.dump(recommendations, f, indent=2)
            logger.info(f"  ✅ Search recommendations JSON saved: {rec_json_path}")
            
            # Save as formatted markdown
            rec_md_path = os.path.join(OUTPUT_FOLDER, "suggested_searches.md")
            md_content = ["# Gap-Closing Literature Search Recommendations\n"]
            md_content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            md_content.append(f"**Total Recommendations:** {len(recommendations)}\n")
            md_content.append("---\n")
            
            # Group by priority
            for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                priority_recs = [r for r in recommendations if r['priority'] == priority]
                if priority_recs:
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
                    md_content.append(f"\n## {emoji[priority]} {priority} Priority ({len(priority_recs)} gaps)\n")
                    
                    for i, rec in enumerate(priority_recs, 1):
                        md_content.append(f"\n### {i}. {rec['pillar']} - {rec['requirement']}")
                        md_content.append(f"**Current Coverage:** {rec['current_completeness']:.1f}%  ")
                        md_content.append(f"**Gap:** {rec['gap_description']}\n")
                        
                        md_content.append("**Suggested Searches:**")
                        for j, search in enumerate(rec['suggested_searches'], 1):
                            md_content.append(f"{j}. `{search['query']}`")
                            md_content.append(f"   - *Rationale:* {search['rationale']}")
                            md_content.append(f"   - *Databases:* {', '.join(search['databases'])}")
                        md_content.append("")
            
            with open(rec_md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_content))
            
            logger.info(f"  ✅ Search recommendations markdown saved: {rec_md_path}")
            safe_print(f"  ✅ Gap-closing search recommendations generated ({len(recommendations)} gaps identified).")
            
            # Generate optimized search plan
            logger.info("Optimizing search strategy based on ROI...")
            try:
                gap_file = os.path.join(OUTPUT_FOLDER, "gap_analysis_report.json")
                optimized_plan_path = os.path.join(OUTPUT_FOLDER, "optimized_search_plan.json")
                
                # Only generate if gap report exists
                if os.path.exists(gap_file):
                    plan = generate_search_plan(
                        gap_file=gap_file,
                        searches_file=rec_json_path,
                        output_file=optimized_plan_path
                    )
                    logger.info(f"  ✅ Optimized search plan saved: {optimized_plan_path}")
                    safe_print(f"  ✅ ROI-optimized search plan generated ({plan['high_priority_searches']} high priority searches).")
                else:
                    logger.warning("  ⚠️ Gap analysis report not found, skipping search optimization")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to generate optimized search plan: {e}")
        else:
            logger.info("  ℹ️ No gap-closing recommendations generated (all areas >50% complete)")
            safe_print("  ℹ️ No critical gaps requiring additional searches.")
            
    except Exception as e:
        error_msg = f"Failed to generate search recommendations: {e}"
        logger.error(error_msg)
        visualization_errors.append(error_msg)
        safe_print(f"  ⚠️ {error_msg}")
    
    # Report any visualization errors
    if visualization_errors:
        logger.warning(f"\n⚠️  {len(visualization_errors)} visualization(s) failed:")
        for error in visualization_errors:
            logger.warning(f"  - {error}")
        safe_print(f"\n⚠️  {len(visualization_errors)} visualization(s) encountered errors (see log for details)")
    else:
        logger.info("\n✅ All visualizations generated successfully!")
        safe_print("\n✅ All visualizations generated successfully!")
    
    # --- Validate Expected Output Files ---
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATING OUTPUT FILES")
    safe_print("\n--- 📋 Validating Output Files ---")
    
    expected_outputs = {
        'Pillar Waterfalls': [f"waterfall_{pname.split(':')[0]}.html" for pname in all_results.keys()],
        'Visualizations': ['_OVERALL_Research_Gap_Radar.html', '_Paper_Network.html', '_Research_Trends.html'],
        'Reports': ['gap_analysis_report.json', 'executive_summary.md', 'suggested_searches.json', 'suggested_searches.md', 'evidence_decay.json', 'optimized_search_plan.json', CONTRIBUTION_REPORT_FILE.split('/')[-1]]
    }
    
    missing_files = []
    found_files = []
    
    for category, files in expected_outputs.items():
        for filename in files:
            filepath = os.path.join(OUTPUT_FOLDER, filename) if not filename.startswith(OUTPUT_FOLDER) else filename
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                found_files.append((filename, file_size))
                logger.info(f"  ✅ {filename} ({file_size:,} bytes)")
            else:
                missing_files.append(filename)
                logger.warning(f"  ❌ {filename} - NOT FOUND")
    
    # Summary
    total_expected = sum(len(files) for files in expected_outputs.values())
    total_found = len(found_files)
    success_rate = (total_found / total_expected * 100) if total_expected > 0 else 0
    
    logger.info(f"\nOutput Generation Summary:")
    logger.info(f"  Found: {total_found}/{total_expected} files ({success_rate:.1f}%)")
    safe_print(f"\n📊 Output Files: {total_found}/{total_expected} generated ({success_rate:.1f}%)")
    
    if missing_files:
        logger.warning(f"  Missing {len(missing_files)} file(s):")
        for filename in missing_files:
            logger.warning(f"    - {filename}")
        safe_print(f"⚠️  {len(missing_files)} expected file(s) not generated (see log)")

    # --- 6. Save Final State ---
    save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history, stage="final")
    
    progress_tracker.emit("visualization", "complete", "All visualizations and reports generated")
    progress_tracker.emit("finalization", "starting", "Finalizing pipeline execution...")

    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    safe_print("\n" + "=" * 80)
    safe_print("ANALYSIS COMPLETE")
    if radar_data:
        safe_print(f"📊 Average completeness: {np.mean(list(radar_data.values())):.1f}% after {iteration_count} iteration(s).")
    safe_print(f"Total time: {(time.time() - global_start_time):.2f} seconds.")
    safe_print(f"Reports saved to '{OUTPUT_FOLDER}'")
    
    progress_tracker.emit("finalization", "complete", f"Pipeline completed in {(time.time() - global_start_time):.2f} seconds")


if __name__ == "__main__":
    main()